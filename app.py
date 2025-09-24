#!/usr/bin/env python3
"""Aplicación gráfica para convertir archivos WAV a MP3 usando ffmpeg."""

from __future__ import annotations

import queue
import subprocess
import threading
from pathlib import Path
from typing import List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def ffmpeg_available() -> bool:
    """Comprueba si el ejecutable ffmpeg está disponible en el PATH."""
    try:
        completed = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError:
        return False
    return completed.returncode == 0


class ConverterApp:
    """Ventana principal de la aplicación."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("2MP3 - Convertidor WAV a MP3")
        self.root.geometry("640x480")
        self.root.resizable(True, True)

        self.selected_files: List[Path] = []
        self.output_dir: Optional[Path] = None
        self.conversion_thread: Optional[threading.Thread] = None
        self.queue: "queue.Queue[str]" = queue.Queue()

        self._build_widgets()
        self._poll_queue()

    def _build_widgets(self) -> None:
        """Crea todos los widgets de la interfaz."""
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sección de selección de archivos
        file_frame = ttk.LabelFrame(main_frame, text="Archivos WAV", padding=12)
        file_frame.pack(fill=tk.BOTH, expand=False)

        ttk.Button(
            file_frame,
            text="Seleccionar archivos",
            command=self.select_files,
        ).pack(side=tk.LEFT)

        self.file_count_var = tk.StringVar(value="Ningún archivo seleccionado")
        ttk.Label(file_frame, textvariable=self.file_count_var).pack(
            side=tk.LEFT, padx=10
        )

        # Lista de archivos seleccionados
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.file_list = tk.Listbox(list_frame, height=8)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.configure(yscrollcommand=scrollbar.set)

        # Sección de carpeta de salida
        output_frame = ttk.LabelFrame(main_frame, text="Carpeta de salida", padding=12)
        output_frame.pack(fill=tk.X, expand=False, pady=(12, 0))

        ttk.Button(
            output_frame,
            text="Seleccionar carpeta",
            command=self.select_output_dir,
        ).pack(side=tk.LEFT)

        self.output_dir_var = tk.StringVar(value="Se guardarán junto al archivo original")
        ttk.Label(output_frame, textvariable=self.output_dir_var).pack(side=tk.LEFT, padx=10)

        # Barra de progreso
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, expand=False, pady=(12, 0))

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, expand=True)

        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W, pady=(8, 0))

        # Botón de conversión
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, expand=False, pady=(12, 0))

        self.convert_button = ttk.Button(
            action_frame,
            text="Convertir a MP3",
            command=self.start_conversion,
        )
        self.convert_button.pack(side=tk.RIGHT)

        # Consola de mensajes
        log_frame = ttk.LabelFrame(main_frame, text="Registro", padding=12)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    # Interacciones de usuario
    def select_files(self) -> None:
        """Abre un diálogo para seleccionar archivos WAV."""
        filenames = filedialog.askopenfilenames(
            title="Seleccionar archivos WAV",
            filetypes=[("Archivos WAV", "*.wav"), ("Todos los archivos", "*.*")],
        )
        if not filenames:
            return

        paths = [Path(name) for name in filenames if Path(name).suffix.lower() == ".wav"]
        if not paths:
            messagebox.showwarning(
                "Sin archivos válidos",
                "No se seleccionaron archivos WAV válidos.",
            )
            return

        self.selected_files = paths
        self.file_list.delete(0, tk.END)
        for path in self.selected_files:
            self.file_list.insert(tk.END, str(path))

        self.file_count_var.set(
            f"{len(self.selected_files)} archivo(s) seleccionado(s)"
        )
        self.log("Se seleccionaron nuevos archivos para convertir.")

    def select_output_dir(self) -> None:
        directory = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not directory:
            return
        self.output_dir = Path(directory)
        self.output_dir_var.set(str(self.output_dir))
        self.log(f"Carpeta de salida establecida en: {self.output_dir}")

    def start_conversion(self) -> None:
        if not self.selected_files:
            messagebox.showinfo(
                "Sin archivos",
                "Selecciona al menos un archivo WAV para convertir.",
            )
            return

        if not ffmpeg_available():
            messagebox.showerror(
                "ffmpeg no encontrado",
                "No se encontró el ejecutable 'ffmpeg'. Asegúrate de que esté instalado y disponible en el PATH.",
            )
            return

        if self.conversion_thread and self.conversion_thread.is_alive():
            messagebox.showinfo(
                "Conversión en progreso",
                "Ya hay una conversión en curso.",
            )
            return

        self.convert_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("Iniciando conversión...")
        self.log("Iniciando conversión de archivos.")

        self.conversion_thread = threading.Thread(
            target=self._convert_files_worker,
            daemon=True,
        )
        self.conversion_thread.start()

    # Hilo de conversión
    def _convert_files_worker(self) -> None:
        total = len(self.selected_files)
        for index, source in enumerate(self.selected_files, start=1):
            try:
                dest_dir = self.output_dir or source.parent
                dest = dest_dir / f"{source.stem}.mp3"
                self._convert_single(source, dest)
                self.queue.put(f"OK: {source.name} → {dest.name}")
            except Exception as exc:  # noqa: BLE001
                self.queue.put(f"ERROR: {source.name} → {exc}")
            finally:
                progress = (index / total) * 100
                self.queue.put(("PROGRESS", progress))

        self.queue.put("FINISHED")

    def _convert_single(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(destination),
        ]
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or "Error desconocido de ffmpeg")

    # Actualización de UI desde el hilo principal
    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "PROGRESS":
                    self.progress_var.set(item[1])
                    self.status_var.set(f"Progreso: {item[1]:.0f}%")
                elif item == "FINISHED":
                    self._on_conversion_finished()
                else:
                    self.log(str(item))
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_queue)

    def _on_conversion_finished(self) -> None:
        self.convert_button.config(state=tk.NORMAL)
        self.status_var.set("Conversión finalizada")
        self.progress_var.set(100)
        self.log("Proceso completado.")

    def log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
