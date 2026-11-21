import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from urllib.parse import unquote, urlparse
from tkinter import filedialog, messagebox, ttk


APP_NAME = "ELG Downloader"
APP_VERSION = "PC V1.4"

BROWSERS = {
    "Sem cookies": None,
    "Chrome": "chrome",
    "Edge": "edge",
    "Firefox": "firefox",
    "Brave": "brave",
    "Chromium": "chromium",
    "Opera": "opera",
    "Vivaldi": "vivaldi",
}

QUALITIES = {
    "Melhor disponível": None,
    "4K / 2160p": 2160,
    "1440p": 1440,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
PROGRESS_PREFIX = "ELG_PROGRESS:"


def clean_ansi(text):
    try:
        return ANSI_RE.sub("", str(text))
    except Exception:
        return str(text)


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} — {APP_VERSION}")
        self.geometry("950x790")
        self.minsize(860, 700)

        self.gui_queue = queue.Queue()
        self.worker = None
        self.active_process = None
        self.process_lock = threading.Lock()
        self.cancel_event = threading.Event()

        default_base = Path.home() / "Downloads" / "ELG Downloader"

        self.mode_var = tk.StringVar(value="audio")
        self.quality_var = tk.StringVar(value="Melhor disponível")
        self.browser_var = tk.StringVar(value="Sem cookies")
        self.output_var = tk.StringVar(value=str(default_base))
        self.playlist_var = tk.BooleanVar(value=True)
        self.cleanup_var = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value="Pronto.")
        self.current_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0.0)

        self._build_ui()
        self.after(100, self._drain_gui_queue)

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text="ELG Downloader",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            root,
            text=(
                "Fila de links • MP3 • vídeo • playlists • HLS/M3U8 • DASH/MPD • "
                "cookies • cancelamento imediato"
            ),
        ).pack(anchor="w", pady=(0, 14))

        link_box = ttk.LabelFrame(root, text="Links — um por linha", padding=10)
        link_box.pack(fill="x")

        text_row = ttk.Frame(link_box)
        text_row.pack(fill="x")

        self.url_text = tk.Text(
            text_row,
            height=6,
            wrap="none",
            font=("Consolas", 10),
        )
        self.url_text.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(text_row, orient="vertical", command=self.url_text.yview)
        scroll.pack(side="right", fill="y")
        self.url_text.configure(yscrollcommand=scroll.set)

        link_buttons = ttk.Frame(link_box)
        link_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(link_buttons, text="Colar", command=self._paste).pack(side="left")
        ttk.Button(
            link_buttons,
            text="Limpar",
            command=lambda: self.url_text.delete("1.0", "end"),
        ).pack(side="left", padx=(8, 0))

        options = ttk.LabelFrame(root, text="Opções", padding=10)
        options.pack(fill="x", pady=(10, 0))

        row1 = ttk.Frame(options)
        row1.pack(fill="x")

        ttk.Label(row1, text="Formato:").pack(side="left")
        ttk.Radiobutton(
            row1,
            text="MP3 192 kbps",
            variable=self.mode_var,
            value="audio",
            command=self._sync_quality,
        ).pack(side="left", padx=(8, 14))

        ttk.Radiobutton(
            row1,
            text="Vídeo MP4",
            variable=self.mode_var,
            value="video",
            command=self._sync_quality,
        ).pack(side="left")

        ttk.Label(row1, text="Qualidade:").pack(side="left", padx=(24, 6))
        self.quality_combo = ttk.Combobox(
            row1,
            textvariable=self.quality_var,
            values=list(QUALITIES),
            state="readonly",
            width=18,
        )
        self.quality_combo.pack(side="left")

        ttk.Label(row1, text="Cookies:").pack(side="left", padx=(24, 6))
        ttk.Combobox(
            row1,
            textvariable=self.browser_var,
            values=list(BROWSERS),
            state="readonly",
            width=14,
        ).pack(side="left")

        row2 = ttk.Frame(options)
        row2.pack(fill="x", pady=(10, 0))

        ttk.Checkbutton(
            row2,
            text="Baixar playlist inteira quando aplicável",
            variable=self.playlist_var,
        ).pack(side="left")

        ttk.Checkbutton(
            row2,
            text="Apagar arquivos parciais ao cancelar",
            variable=self.cleanup_var,
        ).pack(side="left", padx=(24, 0))

        dest = ttk.LabelFrame(root, text="Pasta base de destino", padding=10)
        dest.pack(fill="x", pady=(10, 0))

        ttk.Entry(dest, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(dest, text="Escolher...", command=self._choose_folder).pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(
            root,
            text=(
                "MP3 → Musicas | vídeo → Videos. "
                "O cancelamento encerra a árvore do processo yt-dlp/FFmpeg. "
                "Se o yt-dlp retornar URL não suportada, o app tenta a mesma URL diretamente no FFmpeg (arquivo, M3U8 ou MPD). O aplicativo não remove DRM nem contorna domínios explicitamente recusados pelo yt-dlp."
            ),
            wraplength=900,
        ).pack(anchor="w", pady=(8, 0))

        progress = ttk.LabelFrame(root, text="Andamento", padding=10)
        progress.pack(fill="x", pady=(10, 0))

        ttk.Label(progress, textvariable=self.current_var).pack(anchor="w")
        ttk.Progressbar(
            progress,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        ).pack(fill="x", pady=(6, 4))
        ttk.Label(progress, textvariable=self.status_var).pack(anchor="w")

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", pady=(10, 0))

        self.download_btn = ttk.Button(
            buttons, text="Baixar fila", command=self._start
        )
        self.download_btn.pack(side="left")

        self.cancel_btn = ttk.Button(
            buttons,
            text="Cancelar AGORA",
            command=self._cancel_now,
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=(8, 0))

        ttk.Button(
            buttons, text="Abrir pasta", command=self._open_output
        ).pack(side="left", padx=(8, 0))

        log_box = ttk.LabelFrame(root, text="Log", padding=8)
        log_box.pack(fill="both", expand=True, pady=(10, 0))

        self.log = tk.Text(
            log_box,
            height=15,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
        )
        log_scroll = ttk.Scrollbar(log_box, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        self._sync_quality()

    def _sync_quality(self):
        self.quality_combo.configure(
            state="disabled" if self.mode_var.get() == "audio" else "readonly"
        )

    def _paste(self):
        try:
            clip = self.clipboard_get().strip()
        except tk.TclError:
            return

        if not clip:
            return

        current = self.url_text.get("1.0", "end").strip()
        if current:
            self.url_text.insert("end", "\n" + clip)
        else:
            self.url_text.insert("1.0", clip)

    def _choose_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.output_var.get() or str(Path.home())
        )
        if folder:
            self.output_var.set(folder)

    def _target_dir(self):
        return Path(self.output_var.get()).expanduser() / (
            "Musicas" if self.mode_var.get() == "audio" else "Videos"
        )

    def _open_output(self):
        target = self._target_dir()
        target.mkdir(parents=True, exist_ok=True)

        try:
            if os.name == "nt":
                os.startfile(target)
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", clean_ansi(text).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _emit(self, kind, payload=None):
        self.gui_queue.put((kind, payload))

    def _drain_gui_queue(self):
        try:
            while True:
                kind, payload = self.gui_queue.get_nowait()

                if kind == "log":
                    self._append_log(payload)

                elif kind == "progress":
                    pct, status, title = payload
                    self.progress_var.set(pct)
                    self.status_var.set(status)
                    if title:
                        self.current_var.set(title)

                elif kind == "running":
                    self._set_running(True)

                elif kind == "idle":
                    self._set_running(False)

                elif kind == "done":
                    self._set_running(False)
                    self.progress_var.set(100)
                    self.status_var.set(payload)
                    self._append_log(payload)
                    messagebox.showinfo(APP_NAME, payload)

                elif kind == "cancelled":
                    self._set_running(False)
                    self.status_var.set("Cancelado imediatamente.")
                    self._append_log("CANCELADO: processo yt-dlp/FFmpeg encerrado.")

                elif kind == "fatal":
                    self._set_running(False)
                    self.status_var.set("Erro.")
                    self._append_log("ERRO: " + payload)
                    messagebox.showerror(APP_NAME, payload)

        except queue.Empty:
            pass

        self.after(100, self._drain_gui_queue)

    def _set_running(self, running):
        self.download_btn.configure(state="disabled" if running else "normal")
        self.cancel_btn.configure(state="normal" if running else "disabled")

    def _get_urls(self):
        urls = []
        for raw in self.url_text.get("1.0", "end").splitlines():
            url = raw.strip()
            if url and url not in urls:
                urls.append(url)
        return urls

    def _start(self):
        urls = self._get_urls()

        if not urls:
            messagebox.showwarning(APP_NAME, "Cole pelo menos um link.")
            return

        if any(not (u.startswith("http://") or u.startswith("https://")) for u in urls):
            messagebox.showwarning(
                APP_NAME,
                "Use somente URLs começando com http:// ou https://.",
            )
            return

        if shutil.which("ffmpeg") is None:
            messagebox.showerror(
                APP_NAME,
                "FFmpeg não foi encontrado no PATH.",
            )
            return

        if not self._yt_dlp_command_available():
            messagebox.showerror(
                APP_NAME,
                "yt-dlp não foi encontrado.\n\n"
                "Execute:\npy -3.11 -m pip install --upgrade \"yt-dlp[default,curl-cffi]\" yt-dlp-ejs",
            )
            return

        self.cancel_event.clear()
        self.progress_var.set(0)
        self.current_var.set("")
        self.status_var.set("Preparando...")
        self._set_running(True)

        self.worker = threading.Thread(
            target=self._queue_worker,
            args=(urls,),
            daemon=True,
        )
        self.worker.start()

    def _yt_dlp_command_available(self):
        if getattr(sys, "frozen", False):
            helper = Path(sys.executable).resolve().parent / "ELG_YTDLP_Helper.exe"
            return helper.exists()

        return True

    def _base_command(self):
        if getattr(sys, "frozen", False):
            helper = Path(sys.executable).resolve().parent / "ELG_YTDLP_Helper.exe"
            return [str(helper)]

        return [sys.executable, "-m", "yt_dlp"]

    def _build_command(self, url):
        target = self._target_dir()
        target.mkdir(parents=True, exist_ok=True)

        template = str(
            target / "%(playlist_index&{} - |)s%(title)s [%(id)s].%(ext)s"
        )

        cmd = self._base_command() + [
            "--newline",
            "--no-color",
            "--continue",
            "--retries", "10",
            "--fragment-retries", "10",
            "-o", template,
            "--progress-template",
            "download:ELG_PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(info.title)s",
        ]

        # Histórico somente para playlists inteiras.
        # Em download individual, não consulta nem grava o arquivo de archive,
        # permitindo baixar novamente o mesmo link quantas vezes quiser.
        if self.playlist_var.get():
            archive = target / (
                ".baixados_mp3.txt"
                if self.mode_var.get() == "audio"
                else ".baixados_video.txt"
            )
            cmd += ["--download-archive", str(archive)]
        else:
            cmd += ["--no-playlist"]

        browser = BROWSERS.get(self.browser_var.get())
        if browser:
            cmd += ["--cookies-from-browser", browser]

        if self.mode_var.get() == "audio":
            cmd += [
                "-f", "bestaudio/best",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
            ]
        else:
            height = QUALITIES.get(self.quality_var.get())

            if height is None:
                fmt = "bv*+ba/b"
            else:
                fmt = (
                    f"bv*[height<={height}]+ba/"
                    f"b[height<={height}]"
                )

            cmd += [
                "-f", fmt,
                "--merge-output-format", "mp4",
                "--remux-video", "mp4",
            ]

        cmd.append(url)
        return cmd

    def _spawn(self, cmd):
        kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        if os.name == "nt":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW
            )
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd, **kwargs)

        with self.process_lock:
            self.active_process = proc

        return proc

    def _kill_process_tree(self, proc):
        if proc is None or proc.poll() is not None:
            return

        try:
            if os.name == "nt":
                subprocess.run(
                    [
                        "taskkill",
                        "/PID", str(proc.pid),
                        "/T",
                        "/F",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5,
                )
            else:
                os.killpg(
                    os.getpgid(proc.pid),
                    signal.SIGKILL,
                )
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _cancel_now(self):
        self.cancel_event.set()
        self.status_var.set("Cancelando agora...")

        with self.process_lock:
            proc = self.active_process

        self._kill_process_tree(proc)

    def _cleanup_partial_files(self, target, started_at):
        if not self.cleanup_var.get():
            return

        patterns = (
            "*.part",
            "*.ytdl",
            "*.temp.*",
            "*.frag",
        )

        for pattern in patterns:
            for path in target.glob(pattern):
                try:
                    if path.stat().st_mtime >= started_at - 2:
                        path.unlink()
                        self._emit("log", f"Parcial removido: {path.name}")
                except OSError:
                    pass

    def _parse_progress(self, line):
        if PROGRESS_PREFIX not in line:
            return False

        data = line.split(PROGRESS_PREFIX, 1)[1].strip()
        pieces = data.split("|", 3)

        while len(pieces) < 4:
            pieces.append("")

        pct_text, speed, eta, title = pieces

        try:
            pct = float(pct_text.replace("%", "").strip())
        except ValueError:
            pct = 0.0

        status_bits = []
        if speed and speed != "NA":
            status_bits.append(speed.strip())
        if eta and eta != "NA":
            status_bits.append("ETA " + eta.strip())

        status = " • ".join(status_bits) or f"{pct:.1f}%"

        self._emit(
            "progress",
            (pct, status, title.strip()),
        )
        return True

    def _blocked_by_ytdlp(self, text):
        low = text.lower()
        return (
            "[piracy]" in low
            or "primarily used for piracy" in low
        )

    def _looks_like_drm(self, text):
        low = text.lower()
        return "drm" in low and (
            "protected" in low
            or "encrypted" in low
            or "not supported" in low
        )

    def _unsupported_by_ytdlp(self, text):
        low = text.lower()
        markers = (
            "unsupported url",
            "no suitable extractor",
            "unsupported site",
            "this url is not supported",
            "url not supported",
        )
        return any(marker in low for marker in markers)

    def _unique_output_path(self, path):
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        counter = 2
        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _fallback_basename(self, url):
        parsed = urlparse(url)
        raw_name = Path(unquote(parsed.path)).name

        if raw_name:
            name = Path(raw_name).stem
        else:
            name = "download"

        name = re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" .")
        return name or "download"

    def _run_ffmpeg_fallback(self, url):
        target = self._target_dir()
        target.mkdir(parents=True, exist_ok=True)

        basename = self._fallback_basename(url)

        if self.mode_var.get() == "audio":
            output = self._unique_output_path(target / f"{basename}.mp3")
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-y",
                "-i", url,
                "-vn",
                "-codec:a", "libmp3lame",
                "-b:a", "192k",
                str(output),
            ]
        else:
            output = self._unique_output_path(target / f"{basename}.mp4")
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-y",
                "-i", url,
                "-map", "0:v:0?",
                "-map", "0:a:0?",
                "-c", "copy",
                "-movflags", "+faststart",
                str(output),
            ]

        self._emit(
            "progress",
            (
                0.0,
                "yt-dlp não suporta a URL; tentando FFmpeg direto...",
                output.name,
            ),
        )
        self._emit("log", "Fallback direto ativado: FFmpeg")
        self._emit("log", f"Saída: {output}")

        started_at = time.time()
        proc = self._spawn(cmd)
        captured = []

        try:
            assert proc.stdout is not None

            for raw in proc.stdout:
                line = clean_ansi(raw).rstrip()

                if self.cancel_event.is_set():
                    self._kill_process_tree(proc)
                    break

                if not line:
                    continue

                captured.append(line)

                # Evita poluir o log com cada frame, mas mantém erros e informações úteis.
                if (
                    "error" in line.lower()
                    or "invalid" in line.lower()
                    or "http" in line.lower()
                    or "input #" in line.lower()
                    or "output #" in line.lower()
                    or "duration:" in line.lower()
                ):
                    self._emit("log", line)

            if self.cancel_event.is_set():
                self._kill_process_tree(proc)
                try:
                    proc.wait(timeout=2)
                except Exception:
                    pass

                self._cleanup_partial_files(target, started_at)

                try:
                    if output.exists():
                        output.unlink()
                except OSError:
                    pass

                return "cancelled", ""

            code = proc.wait()

        finally:
            with self.process_lock:
                if self.active_process is proc:
                    self.active_process = None

        if code == 0 and output.exists() and output.stat().st_size > 0:
            self._emit("log", "Fallback FFmpeg concluído com sucesso.")
            return "ok", ""

        try:
            if output.exists() and output.stat().st_size == 0:
                output.unlink()
        except OSError:
            pass

        tail = "\n".join(captured[-10:]).strip()

        return (
            "error",
            "O yt-dlp não suporta essa URL e o FFmpeg também não conseguiu "
            "abri-la como mídia direta/M3U8/MPD. Se for uma página web comum, "
            "forneça o link direto do arquivo ou do manifest.\n\n"
            + (tail or f"FFmpeg terminou com código {code}."),
        )

    def _run_one(self, url):
        target = self._target_dir()
        target.mkdir(parents=True, exist_ok=True)
        started_at = time.time()

        cmd = self._build_command(url)

        self._emit("log", "-" * 68)
        self._emit("log", f"URL: {url}")

        proc = self._spawn(cmd)

        captured = []

        try:
            assert proc.stdout is not None

            for raw in proc.stdout:
                line = clean_ansi(raw).rstrip()

                if self.cancel_event.is_set():
                    self._kill_process_tree(proc)
                    break

                if not line:
                    continue

                captured.append(line)

                if not self._parse_progress(line):
                    self._emit("log", line)

            if self.cancel_event.is_set():
                self._kill_process_tree(proc)
                try:
                    proc.wait(timeout=2)
                except Exception:
                    pass

                self._cleanup_partial_files(target, started_at)
                return "cancelled", ""

            code = proc.wait()

        finally:
            with self.process_lock:
                if self.active_process is proc:
                    self.active_process = None

        combined = "\n".join(captured)

        if code == 0:
            return "ok", ""

        if self._blocked_by_ytdlp(combined):
            return (
                "error",
                "Este domínio é explicitamente recusado pelo yt-dlp. "
                "O ELG Downloader não contorna esse bloqueio.",
            )

        if self._looks_like_drm(combined):
            return (
                "error",
                "O conteúdo parece estar protegido por DRM. "
                "O ELG Downloader não remove DRM.",
            )

        if self._unsupported_by_ytdlp(combined):
            self._emit(
                "log",
                "yt-dlp informou que a URL não é suportada. "
                "Tentando URL direta / M3U8 / MPD pelo FFmpeg...",
            )
            return self._run_ffmpeg_fallback(url)

        tail = "\n".join(captured[-8:]).strip()
        return "error", tail or f"yt-dlp terminou com código {code}."

    def _queue_worker(self, urls):
        successes = 0
        failures = []

        try:
            for index, url in enumerate(urls, 1):
                if self.cancel_event.is_set():
                    self._emit("cancelled")
                    return

                self._emit(
                    "progress",
                    (
                        0.0,
                        f"Fila {index}/{len(urls)}",
                        url,
                    ),
                )
                self._emit("log", f"Fila {index}/{len(urls)}")

                status, detail = self._run_one(url)

                if status == "cancelled":
                    self._emit("cancelled")
                    return

                if status == "ok":
                    successes += 1
                else:
                    failures.append((url, detail))
                    self._emit("log", "FALHOU: " + detail)

            summary = (
                f"Fila concluída: {successes} sucesso(s), "
                f"{len(failures)} falha(s)."
            )

            if failures:
                self._emit("log", "\nRESUMO DAS FALHAS:")
                for url, error in failures:
                    self._emit("log", f"- {url}\n  {error}")

            self._emit("done", summary)

        except Exception as exc:
            self._emit("fatal", clean_ansi(exc))


if __name__ == "__main__":
    DownloaderApp().mainloop()
