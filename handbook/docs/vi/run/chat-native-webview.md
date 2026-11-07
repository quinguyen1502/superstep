# Chat trong ứng dụng native

Hiển thị chat đã xuất bản trong ứng dụng iOS, Android hoặc React Native bằng
WebView mở `https://studio.example.com/c/<slug>?embed=1`. Ứng dụng đăng nhập
người dùng của mình qua một bridge tin nhắn nhỏ; không có SDK Swift hay Kotlin.
Gói giao diện React Native thuần (không dùng WebView) đã có kế hoạch
(TASK-0227) nhưng chưa có.

## Cấu hình chat

1. Xuất bản trang Chat với truy cập bên thứ ba (`app`). Bật thêm truy cập ẩn
   danh nếu cho phép chat trước khi đăng nhập.
2. Tạo app key như trong [Xác thực chat bên thứ ba](chat-third-party-auth.md).
   Trang trong WebView gọi Studio từ chính origin của Studio, nên danh sách
   origin của key phải để trống hoặc có origin Studio
   (ví dụ `https://studio.example.com`).
3. Backend của bạn tạo user token ngắn hạn từ phiên đăng nhập của ứng dụng và
   trả cho ứng dụng. Secret của app key không bao giờ nằm trong ứng dụng.

Không cần **Các site được nhúng chat này**: WebView mở trang làm tài liệu cấp
cao nhất, không nằm trong frame.

## Cách bridge hoạt động

Khi trang thấy kênh native, trang gửi tin nhắn JSON dạng chuỗi cho ứng dụng:

| Tin nhắn | Khi nào | Ứng dụng trả lời |
| --- | --- | --- |
| `{"v":1,"type":"superstep-chat:ready","slug":"support"}` | Đã tải cấu hình chat | `Superstep.identify(token)` với user token mới |
| `{"v":1,"type":"superstep-chat:token-request","id":"native-1","slug":"support"}` | Chat cần token lần nữa, ví dụ khi kết nối lại | `Superstep.identify(token)` với user token mới trong 10 giây |

Kênh native là kênh mà mỗi nền tảng thêm vào trang:

| Nền tảng | Kênh trang dùng | Cách ứng dụng trả lời |
| --- | --- | --- |
| iOS | `window.webkit.messageHandlers.superstep` (`WKScriptMessageHandler` tên `superstep`) | `callAsyncJavaScript` |
| Android | `window.superstep` từ `WebViewCompat.addWebMessageListener` | `evaluateJavascript` |
| React Native | `window.ReactNativeWebView` từ `react-native-webview` | `injectJavaScript` |

Lời gọi `identify(token)` trả lời một yêu cầu token đang chờ chỉ làm mới token;
không đổi người dùng và không tải lại lịch sử. Lời gọi `identify(token)` khác sẽ
chuyển sang người dùng đó. Gọi `Superstep.logout()` khi người dùng đăng xuất khỏi
ứng dụng. Nếu không có trả lời trong 10 giây, chat báo lỗi. Trang chỉ dùng kênh
native khi là tài liệu cấp cao nhất; trong frame, trang vẫn dùng
[bridge của widget](chat-widget.md).

## Quy tắc bảo mật

- Không bao giờ đặt token trong URL, query string hay fragment. Chỉ truyền qua
  `identify`.
- Trên Android, không dùng `addJavascriptInterface`: đối tượng bị lộ cho mọi
  frame và mọi trang WebView tải. Dùng `addWebMessageListener` với origin Studio
  là origin duy nhất được phép.
- Kiểm tra origin và main frame của mỗi tin nhắn trước khi trả lời, và giữ
  WebView trên Studio: mở link khác bằng trình duyệt hệ thống.
- Tạo token ngắn hạn ở backend. Không nhúng secret của app key, personal access
  token hay workflow token vào ứng dụng.

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

`callAsyncJavaScript` truyền token như một tham số, nên token không bị ghép vào
mã JavaScript. `fetchChatToken()` là lời gọi của bạn tới backend của bạn.
Message handler giữ tham chiếu tới đối tượng nhận; gỡ nó khi màn hình đóng.

## Android (Kotlin, WebView)

Thêm `androidx.webkit:webkit` vào ứng dụng.

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

Dùng một `WebViewClient` giữ điều hướng trên `STUDIO` và mở link khác bằng
`Intent`. `JSONObject.quote` thoát token thành chuỗi JavaScript.

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

Dùng được trong ứng dụng Expo và React Native thuần có cài `react-native-webview`.

## Phạm vi đã kiểm thử

Bài kiểm thử end-to-end trên trình duyệt `frontend/e2e/chat-native-bridge.spec.ts`
mở `/c/<slug>?embed=1` làm trang cấp cao nhất trong Chromium và đóng vai ứng dụng
cho cả ba kênh: trả lời `ready` và `token-request` bằng `Superstep.identify`, gửi
tin nhắn, và kiểm tra token không xuất hiện trong URL, tin nhắn gửi ứng dụng hay
storage. Unit test kiểm tra việc làm mới token, thời hạn 10 giây và việc kiểm
tra frame.

Các đoạn mã Swift, Kotlin và React Native ở trên theo API của từng nền tảng
nhưng không được chạy trên thiết bị hay simulator trong CI. Hãy kiểm thử trong
ứng dụng của bạn trước khi phát hành. Tải file trong WebView phụ thuộc vào hỗ
trợ chọn file của từng nền tảng và không nằm trong hướng dẫn này.
