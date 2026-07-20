import pytest
import asyncio
from app.core.config import Settings
from app.services.printer import get_printer_connection_status, get_printer_health, send_print_job

@pytest.fixture
async def temp_printer_server():
    received_data = []
    
    async def handle_client(reader, writer):
        try:
            data = bytearray()
            while True:
                chunk = await reader.read(1024)
                if not chunk:
                    break
                data.extend(chunk)
            received_data.append(bytes(data))
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            
    server = await asyncio.start_server(handle_client, '127.0.0.1', 0)
    addr = server.sockets[0].getsockname()
    port = addr[1]
    
    server_task = asyncio.create_task(server.serve_forever())
    
    yield '127.0.0.1', port, received_data
    
    server.close()
    try:
        await server.wait_closed()
    except Exception:
        pass
    server_task.cancel()

@pytest.mark.asyncio
async def test_printer_healthcheck_ok(temp_printer_server):
    host, port, _ = temp_printer_server
    settings = Settings(
        print_enabled=True,
        printer_host=host,
        printer_port=port
    )
    assert await get_printer_health(settings) is True

@pytest.mark.asyncio
async def test_printer_healthcheck_failed():
    settings = Settings(
        print_enabled=True,
        printer_host='127.0.0.1',
        printer_port=9999
    )
    assert await get_printer_health(settings) is False

@pytest.mark.asyncio
async def test_printer_healthcheck_disabled_still_checks_connection(temp_printer_server):
    host, port, _ = temp_printer_server
    settings = Settings(
        print_enabled=False,
        printer_host=host,
        printer_port=port,
    )
    assert await get_printer_connection_status(settings) == "ok"
    assert await get_printer_health(settings) is True

@pytest.mark.asyncio
async def test_printer_print_success(temp_printer_server):
    host, port, received_data = temp_printer_server
    settings = Settings(
        print_enabled=True,
        printer_host=host,
        printer_port=port,
        printer_use_pjl=False
    )
    test_pdf = b"%PDF-1.4 ... test pdf data"
    await send_print_job(pdf_bytes=test_pdf, settings=settings)
    
    await asyncio.sleep(0.1)
    assert len(received_data) == 1
    assert received_data[0] == test_pdf

@pytest.mark.asyncio
async def test_printer_print_success_with_pjl(temp_printer_server):
    host, port, received_data = temp_printer_server
    settings = Settings(
        print_enabled=True,
        printer_host=host,
        printer_port=port,
        printer_use_pjl=True
    )
    test_pdf = b"%PDF-1.4"
    await send_print_job(pdf_bytes=test_pdf, settings=settings)
    
    await asyncio.sleep(0.1)
    assert len(received_data) == 1
    assert b"@PJL SET PAPER=A4" in received_data[0]
    assert b"@PJL SET MEDIATYPE=PLAIN" in received_data[0]
    assert test_pdf in received_data[0]

@pytest.mark.asyncio
async def test_printer_print_respects_user_print_flag(temp_printer_server):
    host, port, received_data = temp_printer_server
    settings = Settings(
        print_enabled=False,
        printer_host=host,
        printer_port=port,
        printer_use_pjl=False
    )
    with pytest.raises(RuntimeError, match="User printing is disabled"):
        await send_print_job(pdf_bytes=b"data", settings=settings)

    await send_print_job(pdf_bytes=b"data", settings=settings, force=True)
    await asyncio.sleep(0.1)
    assert len(received_data) == 1
    assert received_data[0] == b"data"

@pytest.mark.asyncio
async def test_printer_print_connection_error():
    settings = Settings(
        print_enabled=True,
        printer_host='127.0.0.1',
        printer_port=9999
    )
    with pytest.raises(ConnectionError):
        await send_print_job(pdf_bytes=b"data", settings=settings)
