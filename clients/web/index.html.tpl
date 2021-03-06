<html>

<head>
    <title>StreamSteam Webtracking Demo</title>
    <meta charset="utf-8">
</head>

<body>
<!-- StreamSteam -->
<script type="text/javascript">
  var $TRACKING_SERVER_URL = '{{ tracking_server_url }}';
  var $SITE_ID = 0;

  var _paq = window._paq || [];
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  (function () {
    _paq.push(['setTrackerUrl', $TRACKING_SERVER_URL]);
    _paq.push(['setSiteId', $SITE_ID]);
    var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
    g.type = 'text/javascript';
    g.async = true;
    g.defer = true;
    g.src = 'js/stream_steam.js';
    s.parentNode.insertBefore(g, s);
  })();
</script>
<!-- End StreamSteam Code -->

<h1>Hello StreamSteam!</h1>

<h2>Event Tracking Examples</h2>

<button onclick="_paq.push(['trackEvent', 'player', 'slide', 'volume', 1.0]);">Set Volume to 1.0</button>
<button onclick="_paq.push(['trackEvent', 'player', 'slide', 'volume', 9.5]);">Set volume to  9.5</button>

</body>

</html>
