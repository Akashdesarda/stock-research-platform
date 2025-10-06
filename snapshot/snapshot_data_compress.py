import tarfile
import time
from pathlib import Path

import zstandard as zstd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


def compress_folder(source_dir: Path, output_filename: Path):
    console = Console()
    console.print(f"[bold green]Compressing folder:[/bold green] {source_dir}")
    start_time = time.time()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("Compressing Snapshot Data", start=False)
        progress.start_task(task)
        cctx = zstd.ZstdCompressor(level=22, threads=-1)
        with open(output_filename, "wb") as f_out:
            with cctx.stream_writer(f_out) as compressor:
                with tarfile.open(fileobj=compressor, mode="w|") as tar_out:
                    tar_out.add(source_dir, arcname=source_dir.name)
        progress.update(task, description="Compression complete!")
    elapsed = time.time() - start_time
    console.print(f"[bold green]Archive created:[/bold green] {output_filename}")
    console.print(f"[cyan]Total time taken: {elapsed:.2f} seconds[/cyan]")


if __name__ == "__main__":
    compress_folder(Path("/shared/assets"), Path("assets.tar.zst"))
