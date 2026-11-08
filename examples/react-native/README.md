# Expo chat example

A loopback client for `examples/chat-host`. It signs in as Lan or Minh, stores
the host session cookie, and passes `POST /api/auth/chat-token` to
`@superstep/react-native` as `getToken`. The app-key secret stays in the host
process.

## Run

Start the sample host from the repository root, as described in
`examples/chat-host/README.md`. Then build the SDK and start Expo:

```sh
npm ci --workspace=@superstep/sdk --include-workspace-root=false
npm run build --workspace=@superstep/sdk
cd examples/react-native
npm ci
npx expo start
```

The default host is `http://localhost:5188`. Override it with
`EXPO_PUBLIC_HOST_URL` only when that URL is still the host the sample server
accepts. The sample server rejects any other `Host` header and requires
`Origin: http://localhost:5188` on POST.

On the iOS simulator, `localhost` is the computer running the host. On the
Android emulator, run `adb reverse tcp:5188 tcp:5188` and keep the same URL.
Cleartext HTTP is enabled for this demo only.

`expo-document-picker` is used by this example's `pickFile` prop. The library
itself does not depend on it.

Device screenshots are a manual checklist in `MANUAL.md`. They are not part of
CI, and they are not committed.
