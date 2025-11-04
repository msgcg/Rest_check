import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:ui' as ui;
// Для Completer
import 'package:file_picker/file_picker.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import 'package:flutter/services.dart';

// Для разрешений
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ПоДЕЛИ!',
      theme: ThemeData(
        colorScheme: const ColorScheme.light(
          primary: Color(0xFF12C26A),
          onPrimary: Color(0xFFFFFFFF),
          primaryContainer: Color(0xFF08A552),
          onPrimaryContainer: Color(0xFFFFFFFF),
          secondary: Color(0xFF0A0A0A),
          onSecondary: Color(0xFFFFFFFF),
          secondaryContainer: Color(0xFF1A1A1A),
          onSecondaryContainer: Color(0xFFFFFFFF),
          tertiary: Color(0xFF888888),
          onTertiary: Color(0xFFFFFFFF),
          tertiaryContainer: Color(0xFF444444),
          onTertiaryContainer: Color(0xFFFFFFFF),
          error: Color(0xFFBA1A1A),
          onError: Color(0xFFFFFFFF),
          errorContainer: Color(0xFFFFDAD6),
          onErrorContainer: Color(0xFF410002),
          surface: Color(0xFFE0E0E0),
          onSurface: Color(0xFF000000),
          surfaceContainerHighest: Color(0xFFE0E0E0),
          onSurfaceVariant: Color(0xFF000000),
          outline: Color(0xFF888888),
          shadow: Color(0xFF000000),
          inverseSurface: Color(0xFF1A1A1A),
          onInverseSurface: Color(0xFFE0E0E0),
          inversePrimary: Color(0xFF08A552),
          surfaceTint: Color(0xFF12C26A),
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.transparent,
      ),
      darkTheme: ThemeData(
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF12C26A),
          onPrimary: Color(0xFFFFFFFF),
          primaryContainer: Color(0xFF08A552),
          onPrimaryContainer: Color(0xFFFFFFFF),
          secondary: Color(0xFF0A0A0A),
          onSecondary: Color(0xFFFFFFFF),
          secondaryContainer: Color(0xFF1A1A1A),
          onSecondaryContainer: Color(0xFFFFFFFF),
          tertiary: Color(0xFF888888),
          onTertiary: Color(0xFFFFFFFF),
          tertiaryContainer: Color(0xFF444444),
          onTertiaryContainer: Color(0xFFFFFFFF),
          error: Color(0xFFBA1A1A),
          onError: Color(0xFFFFFFFF),
          errorContainer: Color(0xFFFFDAD6),
          onErrorContainer: Color(0xFF410002),
          surface: Color(0xFF111111),
          onSurface: Color(0xFFE0E0E0),
          surfaceContainerHighest: Color(0xFF111111),
          onSurfaceVariant: Color(0xFFE0E0E0),
          outline: Color(0xFF888888),
          shadow: Color(0xFF000000),
          inverseSurface: Color(0xFFE0E0E0),
          onInverseSurface: Color(0xFF1A1A1A),
          inversePrimary: Color(0xFF08A552),
          surfaceTint: Color(0xFF12C26A),
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.transparent,
      ),
      themeMode: ThemeMode.system,
      home: const MyHomePage(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  late final WebViewController _controller;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  String _currentUrl = 'https://podeli.oneserver.linkpc.net/';
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _initWebView();
  }


  void _initWebView() {
    late final PlatformWebViewControllerCreationParams params;
    if (WebViewPlatform.instance is AndroidWebViewPlatform) {
      // Просто создаем пустые параметры, useHybridComposition больше не нужен
      params = AndroidWebViewControllerCreationParams(); 
    } else {
      params = const PlatformWebViewControllerCreationParams();
    }

    _controller = WebViewController.fromPlatformCreationParams(params)
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.transparent)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (int progress) {
            setState(() {
              _isLoading = progress < 100;
            });
          },
          onPageStarted: (String url) {
            setState(() {
              _currentUrl = url;
              _isLoading = true;
            });
          },
          onPageFinished: (String url) {
            setState(() {
              _currentUrl = url;
              _isLoading = false;
            });

            _syncSystemThemeWithWebView();

            if (url == 'https://podeli.oneserver.linkpc.net/') {
              _scrollToBottom();
            }

            if (url.contains('privacy')) {
              _enableZoomAndSetMinScale();
            } else {
              _disableZoom();
            }
            _controller.runJavaScript('''
              document.addEventListener('copy', function(event) {
                const text = window.getSelection().toString();
                if (text) {
                  ClipboardChannel.postMessage(text);
                }
              });
            ''');
          },
          onWebResourceError: (WebResourceError error) {
            setState(() {
              _isLoading = false;
            });
          },
          onNavigationRequest: (NavigationRequest request) {
            if (request.url.startsWith('https://podeli.oneserver.linkpc.net/')) {
              return NavigationDecision.navigate;
            }
            return NavigationDecision.prevent;
          },
        ),
      )
      ..loadRequest(Uri.parse(_currentUrl))
      ..addJavaScriptChannel(
        'ClipboardChannel',
        onMessageReceived: (JavaScriptMessage message) {
          Clipboard.setData(ClipboardData(text: message.message));
        },
      );

    if (WebViewPlatform.instance is AndroidWebViewPlatform) {
      final androidController = _controller.platform as AndroidWebViewController;
      androidController.setOnShowFileSelector((params) async {
        final result = await FilePicker.platform.pickFiles(
          type: FileType.image,
        );

        if (result != null && result.files.isNotEmpty) {
          return result.files.map((file) => Uri.file(file.path!).toString()).toList();
        }
        return [];
      });
    }
  }

  void _syncSystemThemeWithWebView() async {
    final brightness = ui.PlatformDispatcher.instance.platformBrightness;
    final isDarkMode = brightness == Brightness.dark;

    await _controller.runJavaScript('''
      const isDark = ${isDarkMode ? 'true' : 'false'};
      document.documentElement.style.colorScheme = isDark ? 'dark' : 'light';
      if (isDark) {
        document.body.classList.add('dark-theme');
        document.documentElement.classList.add('dark-theme');
      } else {
        document.body.classList.remove('dark-theme');
        document.documentElement.classList.remove('dark-theme');
      }
    ''');
  }

  void _scrollToBottom() async {
    await _controller.runJavaScript('''
      const containers = [
        document.querySelector('.container-content'),
        document.querySelector('.share-widgets-wrapper'),
        document.body,
        document.documentElement
      ];
      for (const container of containers) {
        if (container && container.scrollHeight > container.clientHeight) {
          container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
          return;
        }
      }
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
    ''');
  }

  void _enableZoomAndSetMinScale() async {
    await _controller.runJavaScript('''
      (function() {
        let meta = document.querySelector('meta[name="viewport"]');
        if (meta) meta.remove();
        meta = document.createElement('meta');
        meta.name = 'viewport';
        meta.content = 'width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0, user-scalable=yes';
        document.head.appendChild(meta);
      })();
    ''');
  }

  void _disableZoom() async {
    await _controller.runJavaScript('''
      (function() {
        let meta = document.querySelector('meta[name="viewport"]');
        if (meta) meta.remove();
        meta = document.createElement('meta');
        meta.name = 'viewport';
        meta.content = 'width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1.0, minimum-scale=1.0';
        document.head.appendChild(meta);
      })();
    ''');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      extendBodyBehindAppBar: true,
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          RefreshIndicator(
            onRefresh: () async {
              await _controller.reload();
            },
            child: WebViewWidget(controller: _controller),
          ),

          if (_isLoading)
            Positioned.fill(
              child: Container(
                color: Colors.black.withValues(alpha: 0.3),
                child: const Center(
                  child: CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    strokeWidth: 3,
                  ),
                ),
              ),
            ),

          Positioned(
            top: 16.0,
            left: 16.0,
            child: SafeArea(
              child: _buildGradientButton(
                icon: Icons.menu,
                onPressed: () => _scaffoldKey.currentState?.openDrawer(),
                isPrimary: false,
              ),
            ),
          ),

          if (_currentUrl.contains('privacy'))
            Positioned(
              top: 16.0,
              left: 90.0,
              child: SafeArea(
                child: _buildGradientButton(
                  icon: Icons.home,
                  onPressed: () {
                    _controller.loadRequest(Uri.parse('https://podeli.oneserver.linkpc.net/'));
                  },
                  isPrimary: false,
                ),
              ),
            ),
        ],
      ),
      drawer: _buildStyledDrawer(context),
    );
  }

  Widget _buildGradientButton({
    required IconData icon,
    required VoidCallback onPressed,
    required bool isPrimary,
  }) {
    final colors = isPrimary
        ? [const Color(0xFF08A552), const Color(0xFF12C26A)]
        : [const Color.fromARGB(255, 0, 0, 0), const Color(0xFF08A552)];

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: colors,
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(25.0),
        boxShadow: [
          BoxShadow(
            color: colors[1].withValues(alpha: 0.3),
            spreadRadius: 1,
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
        border: Border.all(
          color: Colors.transparent,
          width: 1.5,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(25.0),
        child: InkWell(
          borderRadius: BorderRadius.circular(25.0),
          onTap: onPressed,
          splashColor: colors[1].withValues(alpha: 0.3),
          highlightColor: Colors.transparent,
          child: SizedBox(
            width: 50,
            height: 50,
            child: Icon(icon, color: Colors.white, size: 30),
          ),
        ),
      ),
    );
  }

  Widget _buildStyledDrawer(BuildContext context) {
    final theme = Theme.of(context);
    final isDarkMode = theme.brightness == Brightness.dark;
    final surfaceColor = isDarkMode ? const Color(0xFF111111) : Colors.white;

    return Drawer(
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.only(
          topRight: Radius.circular(25),
          bottomRight: Radius.circular(25),
        ),
      ),
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [const Color(0xFF12C26A), const Color(0xFF9FE61F)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: const BorderRadius.only(
            topRight: Radius.circular(25),
            bottomRight: Radius.circular(25),
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF12C26A).withValues(alpha: 0.2),
              spreadRadius: 2,
              blurRadius: 15,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.only(
            topRight: Radius.circular(25),
            bottomRight: Radius.circular(25),
          ),
          child: Container(
            decoration: BoxDecoration(
              color: surfaceColor,
              borderRadius: const BorderRadius.only(
                topRight: Radius.circular(22),
                bottomRight: Radius.circular(22),
              ),
              border: Border.all(
                color: Colors.transparent,
                width: 6,
              ),
            ),
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                DrawerHeader(
                  decoration: BoxDecoration(color: Colors.transparent),
                  child: Text(
                    'Настройки',
                    style: TextStyle(
                      color: isDarkMode ? Colors.white : const Color(0xFF1A1A1A),
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                _buildDrawerItem(
                  context,
                  icon: Icons.privacy_tip,
                  title: 'Политика конфиденциальности',
                  onTap: () {
                    _controller.loadRequest(Uri.parse('https://podeli.oneserver.linkpc.net/privacy'));
                    Navigator.pop(context);
                  },
                  isDarkMode: isDarkMode,
                ),
                _buildDrawerItem(
                  context,
                  icon: Icons.update,
                  title: 'Проверить обновления',
                  onTap: () {
                    launchUrl(Uri.parse('https://github.com/msgcg/Rest_check/releases'));
                    Navigator.pop(context);
                  },
                  isDarkMode: isDarkMode,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDrawerItem(
    BuildContext context, {
    required IconData icon,
    required String title,
    required VoidCallback onTap,
    required bool isDarkMode,
  }) {
    return ListTile(
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [const Color(0xFF08A552), const Color(0xFF12C26A)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: const Color(0xFF12C26A).withValues(alpha: 0.5),
            width: 1,
          ),
        ),
        child: Icon(icon, color: Colors.white, size: 24),
      ),
      title: Text(
        title,
        style: TextStyle(
          color: isDarkMode ? Colors.white : const Color(0xFF1A1A1A),
          fontSize: 17,
          fontWeight: FontWeight.w500,
        ),
      ),
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
    );
  }
}