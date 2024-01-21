import shutil
import urllib.error
import urllib.request
from http import HTTPStatus
from http.client import HTTPResponse
from pathlib import Path
from typing import IO

import rich.progress

from ..app.app_config import (
    app_has_pycurl,
    app_headers,
    app_progress,
    app_stop_event,
    cache_folder,
)
from ..logger import LoggerManager


def dl_core(task_id: rich.progress.TaskID, url, out: IO[bytes], headers: dict[str, str]) -> None:
    CHUNK_SIZE = 8 * 1024

    # make connection
    res: HTTPResponse = urllib.request.urlopen(
        urllib.request.Request(
            url,
            method="GET",
            headers=headers,
        )
    )

    # update total size
    total_size = int(res.headers.get("content-length", 0))
    app_progress.update(task_id, total=total_size)

    while True:
        chunk = res.read(CHUNK_SIZE)
        if not chunk:
            break
        if app_stop_event.is_set():
            break
        out.write(chunk)
        app_progress.update(task_id, advance=len(chunk))

    # close connection
    res.close()

    return  # intended to run in another thread, should return something


def dl_core_curl(task_id: rich.progress.TaskID, url, out: IO[bytes], headers: dict[str, str]):
    # setup callback
    def status(
        dtotal,
        dcurrent,
        utotal,
        ucurrent,
    ):
        app_progress.update(task_id, total=dtotal)
        if app_stop_event.is_set():
            return 1  # https://curl.se/libcurl/c/CURLOPT_XFERINFOFUNCTION.html
        app_progress.update(task_id, completed=dcurrent)
        return

    # setup curl
    import pycurl

    curl = pycurl.Curl()  # type: ignore # noqa

    # set option
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEDATA, out)
    curl.setopt(curl.FOLLOWLOCATION, True)
    curl.setopt(curl.HTTPHEADER, [f"{k}: {v}" for k, v in headers.items()])
    curl.setopt(curl.NOPROGRESS, False)
    curl.setopt(curl.XFERINFOFUNCTION, status)

    # start download
    try:
        curl.perform()
        return_code = HTTPStatus(curl.getinfo(curl.RESPONSE_CODE))
        if return_code != HTTPStatus.OK:
            raise pycurl.error(f"{return_code} {return_code.phrase}, {return_code.description}")  # type: ignore # noqa
    finally:
        curl.close()  # the error will be handled by dl_download

    return  # intended to run in another thread, should return something


def get_dl_worker():
    log = LoggerManager().get_log()
    if app_has_pycurl:
        try:
            import pycurl  # type: ignore # noqa

            return dl_core_curl
        except ImportError:
            log.warning("Failed to import pycurl, would use legacy downloader instead")
            return dl_core
    else:
        return dl_core


def dl(
    task_id: rich.progress.TaskID,
    url: str,
    out: Path,
    progress_name: str = None,
    headers: dict[str, str] = None,
) -> None:
    log = LoggerManager().get_log()

    # setup headers
    if not headers:
        headers = {}
    headers = {**app_headers, **headers}

    # use out.name if progress_name is not set
    progress_name = out.name if (progress_name is None or out.name.lower() != progress_name.lower()) else progress_name

    # ensure parent[s] directory
    out.parent.mkdir(parents=True, exist_ok=True)

    # preparing progress bar
    app_progress.update(task_id, visible=True)

    # update progress bar description
    app_progress.update(
        task_id,
        description=f"{progress_name[:32] + '...' if len(progress_name) > 35 else progress_name}",
    )

    # dl to tempfile
    tmp = Path(out.with_suffix("._incomplete"))
    get_dl_worker()(task_id, url, tmp.open("wb"), headers)

    if app_stop_event.is_set():
        log.info(f"[bright_yellow]Canceled {progress_name}")
    else:
        shutil.move(tmp.absolute(), out.absolute())
        log.info(f"Downloaded {progress_name}")

    # finishing progress bar
    app_progress.update(task_id, visible=False)
    app_progress.stop_task(task_id)

    # remove tmp
    tmp.unlink(missing_ok=True)

    return  # intended to run in another thread, should return something


def download(url: str, file_name: str = None, headers: dict[str, str] = None):
    """
    return path of the file in cache folder, if fail then return None
    """
    log = LoggerManager().get_log()
    retry = 0
    max_retry = 10
    task_id = app_progress.add_task(description="", total=None, visible=False)
    out = cache_folder / file_name
    while not app_stop_event.is_set():
        try:
            dl(task_id, url, out, file_name, headers)
            break
        except Exception as e:
            app_progress.reset(task_id, total=None, visible=False)
            retry += 1
            if retry == max_retry:
                log.warning(f"Reached max retry for {url}, canceling")
                break
            log.warning(
                f"There is an error while downloading {url}\n"
                + f"Attempting to retry. {retry + 1} out of {max_retry}\n"
                + f"[red bold]{type(e).__name__}: [default]{e}",
            )
    if app_stop_event.is_set():
        return
    return out
