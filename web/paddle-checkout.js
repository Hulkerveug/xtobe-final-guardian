// Xtobe Pro landing — Paddle checkout wiring for "Buy Lifetime License — $29"
// Drop BEFORE </body> of the landing page (or import in the React source).
//
// Setup (Paddle dashboard):
//   1. Create product "Xtobe Final Guardian — Lifetime", price $29 one-time
//   2. Copy the Client-side token (live_...) and Price ID (pri_...)
//   3. Add domain xtobe.app under Checkout -> Approved domains
//   4. Webhook: https://xtobe.app/webhooks/paddle -> copy secret to server's
//      PADDLE_WEBHOOK_SECRET. The server auto-issues the XTOBE- key on payment.
//
// Paddle = Merchant of Record: they collect + remit VAT/sales tax worldwide.

(function () {
  var PADDLE_TOKEN = "live_REPLACE_ME";   // or test_... in sandbox
  var PRICE_LIFETIME = "pri_REPLACE_ME";  // $29 one-time price id
  var PRICE_PRO = "pri_REPLACE_ME_PRO";   // $99 one-time price id

  function init() {
    if (!window.Paddle) return;
    // Paddle.Environment.set("sandbox"); // uncomment while testing
    window.Paddle.Initialize({
      token: PADDLE_TOKEN,
      eventCallback: function (e) {
        if (e.name === "checkout.completed") {
          document.dispatchEvent(new CustomEvent("xtobe:purchase-complete"));
          // The license key is emailed by the server webhook (transaction.completed).
          // Show: "Check your email for your XTOBE- license key."
        }
      },
    });
    wire();
  }

  function open(priceId) {
    window.Paddle.Checkout.open({
      items: [{ priceId: priceId, quantity: 1 }],
      settings: { displayMode: "overlay", theme: "dark", locale: "en" },
    });
  }

  function wire() {
    document.querySelectorAll("button, a").forEach(function (el) {
      var t = (el.textContent || "").toLowerCase();
      if (el.dataset.xtobeWired) return;
      if (t.indexOf("buy lifetime") !== -1) {
        el.dataset.xtobeWired = "1";
        el.addEventListener("click", function (ev) {
          ev.preventDefault();
          open(PRICE_LIFETIME);
        });
      } else if (t.indexOf("pro") !== -1 && t.indexOf("99") !== -1) {
        el.dataset.xtobeWired = "1";
        el.addEventListener("click", function (ev) {
          ev.preventDefault();
          open(PRICE_PRO);
        });
      }
    });
  }

  var s = document.createElement("script");
  s.src = "https://cdn.paddle.com/paddle/v2/paddle.js";
  s.onload = init;
  document.head.appendChild(s);
})();
