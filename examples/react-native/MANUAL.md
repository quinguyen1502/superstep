# Manual device checklist

CI runs Jest with a fake socket. It does not boot a simulator or an emulator.
Attach the screenshots from this list to the pull request. Do not commit the
image files.

Start the sample host (`examples/chat-host/README.md`) and this Expo app
(`README.md`). Repeat the same path on an iOS simulator and an Android
emulator (`adb reverse tcp:5188 tcp:5188`).

1. Sign-in screen in English, then switch to Vietnamese.
2. Signed in as Lan, with the empty composer.
3. A sent message and the assistant reply.
4. A text or form question, then the submitted answer.
5. An attached file name in the composer before send.
6. Helpful selected on an assistant turn.
7. The same signed-in chat on the other platform.

Record the simulator and emulator versions next to the images. A missing
device is an open gap, not a passed check.
