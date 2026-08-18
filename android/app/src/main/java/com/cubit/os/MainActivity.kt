package com.cubit.os

import android.annotation.SuppressLint
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Cubit OS free shell:
 * - Starts local uvicorn (Python / Chaquopy) on 127.0.0.1:8765
 * - Loads the same FastAPI + HTMX dashboard in a WebView
 * - No billing, no wallet, no IAP
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var status: TextView
    private val serverStarted = AtomicBoolean(false)
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    private val dashboardUrl = "http://127.0.0.1:8765/"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        status = findViewById(R.id.status)

        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.allowFileAccess = false
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                status.visibility = View.GONE
                webView.visibility = View.VISIBLE
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    status.text = "Waiting for Cubit server…"
                    mainHandler.postDelayed({ webView.loadUrl(dashboardUrl) }, 1500)
                }
            }
        }

        startPythonServer()
    }

    private fun startPythonServer() {
        val dataRoot = filesDir.absolutePath + "/cubit_data"
        executor.execute {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(this))
                }
                val py = Python.getInstance()
                val module = py.getModule("cubit_android_server")
                module.callAttr("start_server", 8765, dataRoot)
                serverStarted.set(true)
                mainHandler.post {
                    status.text = "Loading dashboard…"
                    // Give uvicorn a moment to bind
                    mainHandler.postDelayed({ webView.loadUrl(dashboardUrl) }, 800)
                }
            } catch (e: Exception) {
                mainHandler.post {
                    status.text = "Failed to start Cubit: ${e.message}"
                }
            }
        }
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            @Suppress("DEPRECATION")
            super.onBackPressed()
        }
    }
}
