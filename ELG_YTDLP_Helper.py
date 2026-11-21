import sys
import yt_dlp


def main():
    # O helper existe para que o app compilado consiga iniciar yt-dlp
    # como processo separado e encerrá-lo imediatamente junto com FFmpeg.
    yt_dlp.main()


if __name__ == "__main__":
    main()
