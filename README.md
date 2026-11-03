# Clifford Android app

Reserved development branch for the native Android client. Native app source, Gradle project and APK
have not been implemented yet. The existing responsive browser client is on `web-interface`.

The intended Android client connects to the central kernel over authenticated HTTPS/WSS. Gemma and
Vosk stay on the server; microphone capture, local speech output and playback interruption belong
to the device. No paid model API key belongs in the client. No email integration is planned here now.

[Kernel](https://github.com/parsabe/Clifford/tree/kernel) ·
[API/audio contracts](https://github.com/parsabe/Clifford/blob/documentation/docs/api.md) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)
