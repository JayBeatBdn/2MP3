# 2MP3

Aplicación de escritorio sencilla para convertir archivos de audio **WAV** a **MP3** utilizando `ffmpeg`.

## Requisitos

- Python 3.9 o superior.
- Tkinter (incluido en la mayoría de instalaciones estándar de Python).
- [ffmpeg](https://ffmpeg.org/) instalado y accesible desde la variable de entorno `PATH`.

## Instalación

1. Clona este repositorio.
2. (Opcional) Crea y activa un entorno virtual.
3. No se requieren dependencias adicionales desde `pip`; basta con contar con `ffmpeg`.

## Uso

```bash
python app.py
```

1. Haz clic en **"Seleccionar archivos"** y elige uno o varios archivos WAV.
2. (Opcional) Define una carpeta de salida distinta con **"Seleccionar carpeta"**.
3. Presiona **"Convertir a MP3"** para iniciar el proceso. El registro mostrará el avance y el resultado de cada archivo.

Los MP3 generados conservarán el mismo nombre base que el archivo original y se guardarán en la carpeta seleccionada (o junto al archivo WAV si no se especificó otra ruta).

## Notas

- El botón de conversión se deshabilita mientras está en progreso para evitar ejecuciones simultáneas.
- Si `ffmpeg` no está instalado, la aplicación notificará al usuario y no iniciará la conversión.
