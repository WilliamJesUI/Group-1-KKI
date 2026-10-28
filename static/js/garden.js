document.addEventListener("DOMContentLoaded", () => {
    const createForm = document.getElementById("create-post-form");
    const postList = document.getElementById("post-list");

    const categoryLabels = {
        vegetables: "Vegetables", herbs: "Herbs", flowers: "Flowers", fruits: "Fruits", berries: "Berries",
    };

    function csrfToken(form) {
        return form?.querySelector('[name="csrfmiddlewaretoken"]')?.value || document.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
    }

    async function submitAjax(form) {
        const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken(form) },
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.message || "Error occurred.");
        return data;
    }

    function showConfirmDelete(form, card) {
        const backdrop = document.createElement("div");
        backdrop.style.cssText = "position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(21,35,24,.4);padding:20px;";
        const box = document.createElement("div");
        box.style.cssText = "background:#fff;border:1.5px solid #29382d;border-radius:12px;padding:20px;width:100%;max-width:400px;box-shadow:0 10px 30px rgba(0,0,0,0.2);font-family:Arial,sans-serif;";
        box.innerHTML = `
            <h3 style="margin:0 0 10px;font:bold 18px Georgia,serif;color:#203026;">Delete post?</h3>
            <p style="margin:0 0 20px;font-size:13px;color:#738076;line-height:1.5;">Are you sure you want to delete this post? This action cannot be undone.</p>
            <div style="display:flex;justify-content:flex-end;gap:10px;">
                <button id="cancel-del" style="padding:8px 14px;border:1px solid #c5cec4;border-radius:20px;background:#fff;cursor:pointer;font-weight:bold;font-size:12px;">Cancel</button>
                <button id="confirm-del" style="padding:8px 14px;border:1px solid #9c3535;border-radius:20px;background:#fbeaea;color:#9c3535;cursor:pointer;font-weight:bold;font-size:12px;">Yes, delete</button>
            </div>
        `;
        backdrop.appendChild(box);
        document.body.appendChild(backdrop);

        box.querySelector("#cancel-del").onclick = () => backdrop.remove();
        box.querySelector("#confirm-del").onclick = async () => {
            try {
                await submitAjax(form);
                backdrop.remove();
                card.style.opacity = "0";
                card.style.transform = "translateY(-10px)";
                setTimeout(() => card.remove(), 300);
            } catch (e) {
                alert(e.message);
                backdrop.remove();
            }
        };
    }

    document.addEventListener("click", (e) => {
        const editToggle = e.target.closest(".edit-post-toggle");
        if (editToggle) {
            e.preventDefault();
            const form = editToggle.closest(".garden-post-card")?.querySelector(".garden-edit-form");
            if (form) form.classList.toggle("open");
            return;
        }
        const cancelEdit = e.target.closest(".cancel-post-edit");
        if (cancelEdit) {
            e.preventDefault();
            cancelEdit.closest(".garden-edit-form")?.classList.remove("open");
            return;
        }
    });

    document.addEventListener("submit", async (e) => {
        const form = e.target;

        if (form.id === "create-post-form") {
            e.preventDefault();
            try {
                await submitAjax(form);
                window.location.reload(); 
            } catch (err) {
                alert(err.message);
            }
            return;
        }

        if (form.matches(".garden-delete-form")) {
            e.preventDefault();
            showConfirmDelete(form, form.closest(".garden-post-card"));
            return;
        }

        if (form.matches(".garden-like-form")) {
            e.preventDefault();
            try {
                const data = await submitAjax(form);
                const btn = form.querySelector(".garden-like-button");
                form.querySelector(".like-count").textContent = data.like_count;
                form.querySelector(".like-symbol").textContent = data.liked ? "♥" : "♡";
                btn.classList.toggle("liked", data.liked);
            } catch (err) { alert(err.message); }
            return;
        }

        if (form.matches(".garden-edit-form")) {
            e.preventDefault();
            try {
                const data = await submitAjax(form);
                const card = form.closest(".garden-post-card");
                card.querySelector(".garden-post-caption").textContent = data.caption;
                
                const imgFrame = card.querySelector(".garden-image-frame");
                const img = imgFrame?.querySelector("img");
                if (img && data.image_url) {
                    img.src = data.image_url;
                    imgFrame.hidden = false;
                } else if (imgFrame) {
                    imgFrame.hidden = true;
                }

                form.classList.remove("open");
            } catch (err) { alert(err.message); }
            return;
        }

        if (form.matches(".garden-comment-form")) {
            e.preventDefault();
            try {
                await submitAjax(form);
                window.location.reload(); 
            } catch (err) { alert(err.message); }
            return;
        }
    });
});