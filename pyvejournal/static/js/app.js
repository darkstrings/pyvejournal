// PyveJournal — small progressive enhancements. Everything works without JavaScript.
(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;

  // Mobile menu
  const toggle = document.querySelector("[data-navtoggle]");
  const nav = document.getElementById("sitenav");
  toggle?.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
  });

  // Style picker: switch instantly without a page reload.
  const picker = document.querySelector("[data-stylepick]");
  const select = picker?.querySelector("select");
  select?.addEventListener("change", async () => {
    const body = new FormData(picker);
    try {
      const res = await fetch(picker.action, {
        method: "POST",
        body,
        headers: { Accept: "application/json", "X-CSRFToken": csrf },
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      // On someone else's journal their style stays; elsewhere, show yours right away.
      if (!document.querySelector(".journalhead") || document.documentElement.dataset.mine === "1") {
        document.documentElement.dataset.theme = data.theme;
      }
      flash(data.message, "success");
    } catch {
      picker.submit();
    }
  });

  function flash(message, kind = "info") {
    const box = document.getElementById("flashes");
    if (!box) return;
    const el = document.createElement("div");
    el.className = `flash flash--${kind}`;
    el.setAttribute("role", "status");
    el.textContent = message;
    box.prepend(el);
    setTimeout(() => el.remove(), 4000);
  }

  // Confirm destructive actions.
  document.addEventListener("submit", (e) => {
    const msg = e.target.dataset?.confirm;
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // Threaded replies: "Reply" moves the comment form under that comment.
  const form = document.getElementById("comment-form");
  if (form) {
    const home = form.parentElement;
    const homeNext = form.nextSibling;
    const parentInput = form.querySelector('input[name="parent_id"]');
    const banner = form.querySelector(".commentform__replying");
    const nameEl = form.querySelector("[data-reply-name]");
    const textarea = form.querySelector("textarea");

    document.querySelectorAll("[data-reply]").forEach((btn) =>
      btn.addEventListener("click", () => {
        parentInput.value = btn.dataset.reply;
        nameEl.textContent = btn.dataset.replyTo;
        banner.hidden = false;
        btn.closest(".comment").querySelector(".comment__box").after(form);
        textarea.focus();
      }),
    );
    form.querySelector("[data-reply-cancel]")?.addEventListener("click", () => {
      parentInput.value = "";
      banner.hidden = true;
      home.insertBefore(form, homeNext);
    });
  }
})();
