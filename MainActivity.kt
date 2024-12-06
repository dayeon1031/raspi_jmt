package com.company.parking

import android.os.Bundle
import android.util.Log
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // WebView 초기화
        webView = findViewById(R.id.webView)

        // WebView 설정 적용
        webView.settings.apply {
            javaScriptEnabled = true           // JavaScript 활성화
            domStorageEnabled = true           // DOM Storage 활성화
            cacheMode = WebSettings.LOAD_NO_CACHE  // 캐싱 비활성화
            useWideViewPort = true             // Viewport 메타 태그 활성화
            loadWithOverviewMode = true        // 페이지를 화면 크기에 맞게 로드
        }

        // WebViewClient 설정
        webView.webViewClient = WebViewClient()

        // WebView 디버깅 활성화 (개발 중에만)
        WebView.setWebContentsDebuggingEnabled(true)

        // WebView에서 로드할 URL
        webView.loadUrl("http://172.20.10.12:5000/vehicle")
    }
}
