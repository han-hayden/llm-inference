"""
Core proxy forwarding layer.
Adapted from llm-inference-forward (OpenAI-Forward) project.
Handles transparent request forwarding with SSE streaming and performance metrics extraction.
"""

import asyncio
import json
import time
import uuid
from typing import Optional, Dict, Any

import aiohttp
from fastapi import Request
from loguru import logger
from starlette.responses import StreamingResponse, Response

from ..config import settings


class ProxyForwarder:
    """Transparent proxy with SSE metrics collection."""

    def __init__(self):
        self.client: Optional[aiohttp.ClientSession] = None

    async def start(self):
        timeout = aiohttp.ClientTimeout(total=settings.PROXY_TIMEOUT)
        connector = aiohttp.TCPConnector(
            limit=settings.PROXY_MAX_CONNECTIONS, limit_per_host=0
        )
        self.client = aiohttp.ClientSession(connector=connector, timeout=timeout)
        logger.info("Proxy forwarder started.")

    async def stop(self):
        if self.client:
            await self.client.close()
            logger.info("Proxy forwarder stopped.")

    async def forward(
        self,
        request: Request,
        target_host: str,
        target_port: int,
        path: str,
        collect_metrics: bool = False,
    ) -> Response:
        """
        Forward request to target and optionally collect metrics.

        When collect_metrics is True:
        - Force stream=true + stream_options.include_usage=true
        - Extract TTFT, TPOT, TPS, token counts, cache hits from SSE chunks
        - If original request was non-stream, reassemble into single JSON response
        """
        request_id = str(uuid.uuid4())
        arrival_time = time.time()
        body = await request.body()
        target_url = f"http://{target_host}:{target_port}{path}"

        # Prepare headers (remove hop-by-hop)
        fwd_headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ("host", "content-length", "transfer-encoding"):
                fwd_headers[k] = v

        # Parse payload for stream manipulation
        original_stream = True
        original_include_usage = False
        force_conversion = False
        payload_dict = None

        if collect_metrics and body:
            try:
                payload_dict = json.loads(body)
                original_stream = payload_dict.get("stream", False)

                # Force streaming for metrics collection
                payload_dict["stream"] = True
                if not isinstance(payload_dict.get("stream_options"), dict):
                    payload_dict["stream_options"] = {}
                original_include_usage = payload_dict["stream_options"].get(
                    "include_usage", False
                )
                payload_dict["stream_options"]["include_usage"] = True

                if not original_stream:
                    force_conversion = True

                body = json.dumps(payload_dict).encode("utf-8")
            except (json.JSONDecodeError, AttributeError):
                collect_metrics = False

        fwd_headers["content-length"] = str(len(body))

        try:
            resp = await self.client.request(
                method=request.method,
                url=target_url,
                data=body,
                headers=fwd_headers,
            )
        except Exception as e:
            logger.error(f"Proxy forward failed: {e}")
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=502,
                media_type="application/json",
            )

        if not collect_metrics:
            return StreamingResponse(
                content=self._passthrough(resp),
                status_code=resp.status,
                media_type=resp.content_type,
            )

        # Metrics collection path
        meta = {
            "request_id": request_id,
            "arrival_time": arrival_time,
            "model": payload_dict.get("model", "unknown") if payload_dict else "unknown",
            "messages": payload_dict.get("messages", []) if payload_dict else [],
            "original_stream": original_stream,
            "original_include_usage": original_include_usage,
        }

        if force_conversion:
            return StreamingResponse(
                content=self._collect_and_convert(resp, meta),
                status_code=resp.status,
                media_type="application/json",
            )
        else:
            return StreamingResponse(
                content=self._collect_streaming(resp, meta),
                status_code=resp.status,
                media_type="text/event-stream",
            )

    # ------------------------------------------------------------------
    # Internal generators
    # ------------------------------------------------------------------

    async def _passthrough(self, resp: aiohttp.ClientResponse):
        """Simple byte passthrough."""
        async for chunk in resp.content.iter_any():
            yield chunk

    async def _collect_streaming(
        self, resp: aiohttp.ClientResponse, meta: dict
    ):
        """
        Stream SSE to client while collecting metrics.
        Handles SSE message boundary detection (\\n\\n).
        """
        remaining = b""
        first_token_time = None
        chunk_count = 0
        usage_data: Dict[str, Any] = {}
        response_parts = []
        model = meta["model"]

        async for raw_chunk in resp.content.iter_any():
            combined = remaining + raw_chunk

            while b"\n\n" in combined:
                boundary = combined.find(b"\n\n") + 2
                complete_msg = combined[:boundary]
                combined = combined[boundary:]

                # Parse for metrics
                self._extract_chunk_metrics(
                    complete_msg, meta, response_parts,
                    usage_data, first_token_time, chunk_count,
                )
                msg_str = complete_msg.decode("utf-8", errors="replace")
                for line in msg_str.strip().split("\n"):
                    if line.startswith("data: ") and line[6:].strip() not in ("[DONE]", ""):
                        try:
                            data = json.loads(line[6:])
                            if data.get("usage"):
                                usage_data = data["usage"]
                                model = data.get("model", model)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    response_parts.append(content)
                                    if first_token_time is None:
                                        first_token_time = time.time()
                            chunk_count += 1
                        except json.JSONDecodeError:
                            pass

                # Decide whether to forward usage chunk
                if not meta["original_include_usage"] and usage_data:
                    # Check if this chunk IS the usage-only chunk
                    pass  # still forward for simplicity

                yield complete_msg

            remaining = combined

        if remaining:
            yield remaining

        # Record metrics after stream completes
        completion_time = time.time()
        stat = self._build_stat(
            meta, first_token_time, completion_time, chunk_count,
            usage_data, response_parts, model,
        )
        await self._emit_stat(stat)

    async def _collect_and_convert(
        self, resp: aiohttp.ClientResponse, meta: dict
    ):
        """
        Collect all SSE chunks, extract metrics, then yield a single non-streaming JSON response.
        """
        remaining = b""
        first_token_time = None
        chunk_count = 0
        usage_data: Dict[str, Any] = {}
        response_parts = []
        model = meta["model"]
        finish_reason = "stop"
        request_id_from_server = None

        async for raw_chunk in resp.content.iter_any():
            combined = remaining + raw_chunk

            while b"\n\n" in combined:
                boundary = combined.find(b"\n\n") + 2
                complete_msg = combined[:boundary]
                combined = combined[boundary:]

                msg_str = complete_msg.decode("utf-8", errors="replace")
                for line in msg_str.strip().split("\n"):
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload in ("[DONE]", ""):
                        continue
                    try:
                        data = json.loads(payload)
                        if not request_id_from_server:
                            request_id_from_server = data.get("id")
                        if data.get("usage"):
                            usage_data = data["usage"]
                        model = data.get("model", model)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                response_parts.append(content)
                                if first_token_time is None:
                                    first_token_time = time.time()
                            fr = choices[0].get("finish_reason")
                            if fr:
                                finish_reason = fr
                        chunk_count += 1
                    except json.JSONDecodeError:
                        pass

            remaining = combined

        # Handle any remaining data
        if remaining:
            msg_str = remaining.decode("utf-8", errors="replace")
            for line in msg_str.strip().split("\n"):
                if line.startswith("data: "):
                    payload = line[6:].strip()
                    if payload not in ("[DONE]", ""):
                        try:
                            data = json.loads(payload)
                            if data.get("usage"):
                                usage_data = data["usage"]
                        except json.JSONDecodeError:
                            pass

        completion_time = time.time()
        complete_content = "".join(response_parts)

        # Build non-streaming response
        non_stream_resp = {
            "id": request_id_from_server or meta["request_id"],
            "object": "chat.completion",
            "created": int(meta["arrival_time"]),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": complete_content},
                    "finish_reason": finish_reason,
                }
            ],
        }
        if usage_data and meta["original_include_usage"]:
            non_stream_resp["usage"] = usage_data

        yield json.dumps(non_stream_resp, ensure_ascii=False).encode("utf-8")

        # Record metrics
        stat = self._build_stat(
            meta, first_token_time, completion_time, chunk_count,
            usage_data, response_parts, model,
        )
        await self._emit_stat(stat)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_chunk_metrics(self, chunk_bytes, meta, response_parts,
                                usage_data, first_token_time, chunk_count):
        """Placeholder for inline metric extraction (used by _collect_streaming)."""
        pass

    def _build_stat(
        self, meta, first_token_time, completion_time, chunk_count,
        usage_data, response_parts, model,
    ) -> dict:
        arrival = meta["arrival_time"]
        ttft = (first_token_time - arrival) * 1000 if first_token_time else 0
        e2e = (completion_time - arrival) * 1000
        decode_time = (completion_time - first_token_time) if first_token_time else 0

        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", 0)

        # Extract cached tokens (sglang / vLLM)
        details = usage_data.get("prompt_tokens_details") or {}
        cached_tokens = details.get("cached_tokens", usage_data.get("num_cached_tokens", 0))
        if cached_tokens is None:
            cached_tokens = 0

        output_count = completion_tokens if completion_tokens > 0 else max(chunk_count - 1, 0)
        tpot = (decode_time * 1000 / output_count) if output_count > 0 and decode_time > 0 else 0
        tps = (output_count / decode_time) if decode_time > 0 else 0

        return {
            "request_id": meta["request_id"],
            "model": model,
            "arrival_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(arrival)),
            "completion_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(completion_time)),
            "prompt_tokens": prompt_tokens,
            "forward_cal_tokens": 0,
            "cached_tokens": cached_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "ttft_ms": round(ttft, 2),
            "tpot_ms": round(tpot, 2),
            "tps": round(tps, 2),
            "e2e_latency_ms": round(e2e, 2),
            "chunk_count": chunk_count,
            "messages": meta.get("messages", []),
            "response_content": "".join(response_parts),
        }

    async def _emit_stat(self, stat: dict):
        """Send stat to active collection task (if any)."""
        from ..collect.task_manager import collection_manager

        if collection_manager.has_active_task():
            await collection_manager.add_record(stat)


proxy_forwarder = ProxyForwarder()
