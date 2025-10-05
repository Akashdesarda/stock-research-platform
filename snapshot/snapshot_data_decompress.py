import os
import tarfile
import time

import zstandard as zstd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


def is_dir_empty(path):
    return not any(os.scandir(path))


def decompress_archive(archive_path, extract_dir, force_decompression=False):
    console = Console()
    if not force_decompression and not is_dir_empty(extract_dir):
        console.print(
            f"[yellow]Skipping decompression: {extract_dir} is not empty.[/yellow]"
        )
        return

    start_time = time.time()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("Decompressing snapshot data", start=False)
        progress.start_task(task)
        dctx = zstd.ZstdDecompressor()
        with open(archive_path, "rb") as f_in:
            with dctx.stream_reader(f_in) as decompressor:
                with tarfile.open(fileobj=decompressor, mode="r|") as tar_in:
                    tar_in.extractall(path=extract_dir)
        progress.update(task, description="Decompression complete!")
    elapsed = time.time() - start_time
    console.print(f"[bold green]Archive extracted to:[/bold green] {extract_dir}")
    console.print(f"[cyan]Total time taken: {elapsed:.2f} seconds[/cyan]")


if __name__ == "__main__":
    FORCE_DECOMPRESSION = (
        os.environ.get("FORCE_DECOMPRESSION", "false").lower() == "true"
    )
    decompress_archive(
        "assets.tar.zst", "/assets", force_decompression=FORCE_DECOMPRESSION
    )
