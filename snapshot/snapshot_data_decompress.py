import os
import shutil
import tarfile
import time
from pathlib import Path

import zstandard as zstd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def is_dir_empty(path: Path):
    # Return True if directory does not exist or is empty
    return not any(path.iterdir()) if path.exists() else True


def decompress_archive(
    archive_path: Path, extract_dir: Path, force_decompression=False
):
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
        Path("assets.tar.zst"), Path("/shared"), force_decompression=FORCE_DECOMPRESSION
    )
    console.print(
        "[bold green]copying config.toml to shared assets directory...[/bold green]"
    )
    shutil.copy("/tmp/config.toml", "/shared/assets/config.toml")
    console.print("[bold green]config.toml copied successfully![/bold green]")
