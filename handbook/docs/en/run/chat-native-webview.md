# Chat in a native app

Show a published chat inside an iOS, Android or React Native app with a
WebView of `https://studio.example.com/c/<slug>?embed=1`. The app signs its
own users in through a small message bridge; there is no Swift or Kotlin SDK.
For a native React Native interface instead of a WebView, a separate package is
planned (TASK-0227) and is not available yet.

## Set up the chat

1. Publish the Chat page with third-party access (`app`). Add anonymous access
   too if people may chat before they sign in.
2. Create an app key as described in [Third-party authentication](chat-third-party-auth.md).
   The page in the WebView calls the Studio from the Studio's own origin, so
   the key's allowed origins must be empty or include the Studio origin
   (for example `https://studio.example.com`).
3. Your backend mints a short-lived user token from the app's own signed-in
   session and returns it to the app. The app key secret never goes into the app.

**Sites that may embed this chat** is not needed: the WebView loads the page
as its top-level document, not inside a frame.

## How the bridge works

When the page finds a native channel, it sends JSON text messages to the app:

| Message | When | The app answers |
| --- | --- | --- |
| `{"v":1,"type":"superstep-chat:ready","slug":"support"}` | The chat settings loaded | `Superstep.identify(token)` with a fresh user token |
| `{"v":1,"type":"superstep-chat:token-request","id":"native-1","slug":"support"}` | The chat needs a token again, for example to reconnect | `Superstep.identify(token)` with a fresh user token within 10 seconds |

The native channel is the one each platform adds to the page:

| Platform | Channel the page uses | How the app answers |
| --- | --- | --- |
| iOS | `window.webkit.messageHandlers.superstep` (a `WKScriptMessageHandler` named `superstep`) | `callAsyncJavaScript` |
| Android | `window.superstep` from `WebViewCompat.addWebMessageListener` | `evaluateJavascript` |
| React Native | `window.ReactNativeWebView` from `react-native-webview` | `injectJavaScript` |

An `identify(token)` call that answers a pending token request only refreshes
the token; it does not switch the user or reload the history. Any other
`identify(token)` call switches to that user. Call `Superstep.logout()` when the
person signs out of your app. Without an answer within 10 seconds, the chat
shows an error. The page only uses a native channel when it is the top-level
document; inside a frame it keeps the [widget bridge](chat-widget.md).

## Security rules

- Never put a token in the URL, its query string or fragment. Pass it only
  through `identify`.
- On Android, do not use `addJavascriptInterface`. It exposes the object to
  every frame and every page the WebView loads. Use `addWebMessageListener`
  with the Studio origin as the only allowed origin.
- Check the origin and main frame of every message before you answer, and keep
  the WebView on the Studio: open other links in the system browser.
- Mint tokens on your backend with a short lifetime. Do not embed the app key
  secret, a personal access token or a workflow token in the app.

## iOS (Swift, WKWebView)

```swift
import UIKit
import WebKit

final class SupportChatViewController: UIViewController, WKScriptMessageHandler, WKNavigationDelegate {
    private let studio = URL(string: "https://studio.example.com")!
    private var webView: WKWebView!

    override func viewDidLoad() {
        super.viewDidLoad()
        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "superstep")
        webView = WKWebView(frame: view.bounds, configuration: config)
        webView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        webView.navigationDelegate = self
        view.addSubview(webView)
        webView.load(URLRequest(url: URL(string: "/c/support?embed=1", relativeTo: studio)!))
    }

    deinit { webView?.configuration.userContentController.removeScriptMessageHandler(forName: "superstep") }

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        let origin = message.frameInfo.securityOrigin
        guard message.frameInfo.isMainFrame, origin.protocol == studio.scheme, origin.host == studio.host,
              let text = message.body as? String,
              let json = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any],
              let type = json["type"] as? String,
              type == "superstep-chat:ready" || type == "superstep-chat:token-request" else { return }
        Task { @MainActor in
            guard let token = try? await fetchChatToken() else { return }   // your backend, your session
            _ = try? await webView.callAsyncJavaScript(
                "await window.Superstep.identify(token)", arguments: ["token": token], contentWorld: .page)
        }
    }

    // Keep the WebView on the Studio; open other links outside the app.
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url, url.host != studio.host else { return decisionHandler(.allow) }
        if action.targetFrame?.isMainFrame ?? true { UIApplication.shared.open(url); return decisionHandler(.cancel) }
        decisionHandler(.allow)
    }
}
```

`callAsyncJavaScript` passes the token as an argument, so it is never built
into JavaScript source. `fetchChatToken()` is your own call to your backend.
The message handler retains its target; remove it when the screen goes away.

## Android (Kotlin, WebView)

Add `androidx.webkit:webkit` to the app.

```kotlin
import android.annotation.SuppressLint
import android.net.Uri
import android.webkit.WebView
import androidx.lifecycle.LifecycleCoroutineScope
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import kotlinx.coroutines.launch
import org.json.JSONObject

const val STUDIO = "https://studio.example.com"

@SuppressLint("SetJavaScriptEnabled")
fun showSupportChat(webView: WebView, scope: LifecycleCoroutineScope, fetchChatToken: suspend () -> String?) {
    webView.settings.javaScriptEnabled = true
    if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
        WebViewCompat.addWebMessageListener(webView, "superstep", setOf(STUDIO)) { view, message, sourceOrigin, isMainFrame, _ ->
            if (!isMainFrame || sourceOrigin.toString() != STUDIO) return@addWebMessageListener
            val type = runCatching { JSONObject(message.data ?: "").optString("type") }.getOrDefault("")
            if (type != "superstep-chat:ready" && type != "superstep-chat:token-request") return@addWebMessageListener
            scope.launch {
                val token = fetchChatToken() ?: return@launch          // your backend, your session
                val page = Uri.parse(view.url ?: return@launch)
                if ("${page.scheme}://${page.authority}" != STUDIO) return@launch
                view.evaluateJavascript("void window.Superstep.identify(${JSONObject.quote(token)});", null)
            }
        }
    }
    // Without WEB_MESSAGE_LISTENER the chat still works for anonymous access; do not fall back to addJavascriptInterface.
    webView.loadUrl("$STUDIO/c/support?embed=1")
}
```

Use a `WebViewClient` that keeps navigation on `STUDIO` and opens other links
with an `Intent`. `JSONObject.quote` escapes the token as a JavaScript string.

## React Native (react-native-webview)

```tsx
import { useRef } from 'react'
import { Linking } from 'react-native'
import { WebView, type WebViewMessageEvent } from 'react-native-webview'

const STUDIO = 'https://studio.example.com'
const onStudio = (url: string) => url === STUDIO || url.startsWith(`${STUDIO}/`)

export function SupportChat({ getChatToken }: { getChatToken: () => Promise<string> }) {
  const webView = useRef<WebView>(null)
  const onMessage = async (event: WebViewMessageEvent) => {
    if (!onStudio(event.nativeEvent.url)) return
    let type = ''
    try { type = JSON.parse(event.nativeEvent.data).type } catch { return }
    if (type !== 'superstep-chat:ready' && type !== 'superstep-chat:token-request') return
    const token = await getChatToken()   // your backend, your session
    webView.current?.injectJavaScript(`void window.Superstep.identify(${JSON.stringify(token)}); true;`)
  }
  return <WebView ref={webView} source={{ uri: `${STUDIO}/c/support?embed=1` }} originWhitelist={[STUDIO]}
    onMessage={onMessage}
    onShouldStartLoadWithRequest={request => { if (onStudio(request.url)) return true; void Linking.openURL(request.url); return false }} />
}
```

This works in Expo and bare React Native apps that install `react-native-webview`.

## What is tested

The browser end-to-end test `frontend/e2e/chat-native-bridge.spec.ts` opens
`/c/<slug>?embed=1` as a top-level page in Chromium and plays the app's part for
each of the three channels: it answers `ready` and `token-request` with
`Superstep.identify`, sends a message, and checks that tokens never reach the
URL, the messages to the app or storage. Unit tests cover the refresh,
the 10 second timeout and the frame check.

The Swift, Kotlin and React Native snippets above follow the platform APIs but
are not run on a device or simulator in CI. Test them in your app before release.
File uploads inside a WebView depend on the platform's file chooser support and
are not covered by this guide.
