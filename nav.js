// One navigation bar shared by every page. Add a page here and it appears everywhere.
const PAGES = [
  { href: "browse.html", label: "Browse" },
];

(function () {
  const here = location.pathname.split("/").pop() || "index.html";
  const nav = document.createElement("nav");
  nav.className = "nav";
  const brand = document.createElement("span");
  brand.className = "brand";
  brand.textContent = "Job Watcher";
  nav.appendChild(brand);
  for (const p of PAGES) {
    const a = document.createElement("a");
    a.href = p.href;
    a.textContent = p.label;
    if (p.href === here) a.className = "active";
    nav.appendChild(a);
  }
  document.body.prepend(nav);
})();
