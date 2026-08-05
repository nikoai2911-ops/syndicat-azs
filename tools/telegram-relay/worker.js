// Cloudflare Worker: релей заявок с sd-kt.ru в Telegram-группу.
// Деплой и настройка — см. ИНСТРУКЦИЯ.md рядом с этим файлом.
// Секреты воркера (Settings → Variables and Secrets):
//   BOT_TOKEN — токен бота @syndicatru_bot от @BotFather
//   CHAT_ID   — id группы (отрицательное число, как его узнать — в инструкции)

const ORIGINS = ["https://sd-kt.ru", "https://www.sd-kt.ru"];

function corsHeaders(req) {
  const o = req.headers.get("Origin") || "";
  return {
    "Access-Control-Allow-Origin": ORIGINS.includes(o) ? o : ORIGINS[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

const esc = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS")
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    if (request.method !== "POST")
      return new Response("SYNDICAT relay: OK", { status: 200 });

    let fields = {};
    try {
      const ct = (request.headers.get("Content-Type") || "").toLowerCase();
      if (ct.includes("application/json")) {
        fields = await request.json();
      } else {
        const fd = await request.formData();
        for (const [k, v] of fd.entries())
          if (typeof v === "string") fields[k] = v;
      }
    } catch (e) {}

    // скрытое поле-приманка: человек его не видит и не заполняет, спам-бот заполнит
    if (fields._gotcha)
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json", ...corsHeaders(request) },
      });

    const rows = Object.entries(fields)
      .filter(([k, v]) => !k.startsWith("_") && String(v).trim())
      .map(([k, v]) => `<b>${esc(k)}:</b> ${esc(String(v).slice(0, 800))}`);

    const text = [
      "🔔 <b>Заявка с сайта sd-kt.ru</b>",
      ...(rows.length ? rows : ["(пустая форма)"]),
    ].join("\n");

    let sent = false;
    try {
      const r = await fetch(
        `https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_id: env.CHAT_ID,
            text,
            parse_mode: "HTML",
          }),
        }
      );
      sent = r.ok;
    } catch (e) {}

    // если форму отправили напрямую на воркер (без JS) — вернуть человека на «спасибо»
    if ((request.headers.get("Accept") || "").includes("text/html"))
      return Response.redirect("https://sd-kt.ru/thanks.html", 302);

    return new Response(JSON.stringify({ ok: sent }), {
      headers: { "Content-Type": "application/json", ...corsHeaders(request) },
    });
  },
};
