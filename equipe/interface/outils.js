// Ce que partagent les deux volets de la page : les formats, de petits constructeurs,
// la bulle au survol, le compteur animé, et les messages qu'ils s'envoient.
window.AL = (() => {
  const SVG = "http://www.w3.org/2000/svg";
  const fr = (n, decimales = 0) => n.toLocaleString("fr-FR", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
  const part = (n, total) => (total ? `${fr((100 * n) / total, 1)} %` : "—");
  const id = (nom) => document.getElementById(nom);

  function html(balise, classe, texte) {
    const noeud = document.createElement(balise);
    if (classe) noeud.className = classe;
    if (texte !== undefined) noeud.textContent = texte;
    return noeud;
  }

  function svg(balise, attributs, texte) {
    const noeud = document.createElementNS(SVG, balise);
    for (const [nom, valeur] of Object.entries(attributs)) noeud.setAttribute(nom, valeur);
    if (texte !== undefined) noeud.textContent = texte;
    return noeud;
  }

  // --- La bulle : au survol comme au clavier, le chiffre d'abord, son nom ensuite. ---
  // valeur et nom sont des textes, ou des fonctions quand ils changent avec le filtre (les plots de la puce).
  const bulle = id("bulle");

  function survolable(cible, valeur, nom, entrer, sortir) {
    const lire = (texte) => (typeof texte === "function" ? texte() : texte);
    if (typeof valeur !== "function") {
      cible.setAttribute("tabindex", "0");
      cible.setAttribute("aria-label", `${nom} : ${valeur}`);
    }
    const montrer = (evenement) => {
      bulle.replaceChildren(html("strong", "", lire(valeur)), document.createTextNode(lire(nom)));
      bulle.hidden = false;
      const cadre = cible.getBoundingClientRect();
      const x = evenement.clientX || cadre.left + cadre.width / 2;
      const y = evenement.clientY || cadre.top;
      bulle.style.left = `${Math.max(8, Math.min(x - bulle.offsetWidth / 2, window.innerWidth - bulle.offsetWidth - 8))}px`;
      bulle.style.top = `${Math.max(8, y - bulle.offsetHeight - 12)}px`;
      if (entrer) entrer();
    };
    const cacher = () => { bulle.hidden = true; if (sortir) sortir(); };
    cible.addEventListener("pointermove", montrer);
    cible.addEventListener("pointerleave", cacher);
    cible.addEventListener("focus", montrer);
    cible.addEventListener("blur", cacher);
  }

  // --- Les mêmes chiffres en tableau. ---
  function table(cible, entetes, lignes) {
    const tableau = id(cible);
    tableau.replaceChildren();
    const tete = tableau.createTHead().insertRow();
    entetes.forEach((entete, i) => {
      const cellule = html("th", i ? "n" : "", entete);
      cellule.scope = "col";
      tete.append(cellule);
    });
    const corps = tableau.createTBody();
    for (const ligne of lignes) {
      const rangee = corps.insertRow();
      ligne.forEach((texte, i) => rangee.append(html("td", i ? "n" : "", texte)));
    }
  }

  // Fait défiler un nombre de depart à cible ; ecrire met en forme chaque valeur intermédiaire.
  function compter(noeud, depart, cible, ecrire, duree = 550) {
    cancelAnimationFrame(noeud.image);
    const debut = performance.now();
    const avancer = (instant) => {
      const avance = Math.min(1, Math.max(0, (instant - debut) / duree));
      noeud.textContent = ecrire(depart + (cible - depart) * (1 - (1 - avance) ** 3));
      if (avance < 1) noeud.image = requestAnimationFrame(avancer);
    };
    noeud.image = requestAnimationFrame(avancer);
  }

  // Glisse le curseur d'un groupe (filtre, onglets) sous son élément actif.
  function placer(groupe, actif) {
    groupe.style.setProperty("--x", `${actif.offsetLeft}px`);
    groupe.style.setProperty("--l", `${actif.offsetWidth}px`);
    groupe.classList.add("pret");
  }
  // Le curseur du filtre est posé tout de suite, sans attendre les données.
  placer(id("filtre"), id("filtre").querySelector("input:checked").nextElementSibling);

  // Les deux volets ne se connaissent pas : ils se parlent par des messages.
  //   « piste »    l'explorateur a une question à suggérer, d'après ce qui vient d'être choisi
  //   « proposer » une question à mettre dans le champ, sans l'envoyer
  //   « montrer »  l'agent demande d'ouvrir une colonne dans l'explorateur
  const dire = (nom, detail) => document.dispatchEvent(new CustomEvent(nom, { detail }));
  const entendre = (nom, suite) => document.addEventListener(nom, (evenement) => suite(evenement.detail));

  // Sur un écran étroit, un seul volet est visible : « donnees » ou « agent ».
  function volet(nom) {
    id("app").dataset.volet = nom;
    for (const bouton of id("volets").querySelectorAll("button")) bouton.setAttribute("aria-pressed", String(bouton.dataset.volet === nom));
  }
  id("volets").addEventListener("click", (evenement) => {
    const bouton = evenement.target.closest("button");
    if (bouton) volet(bouton.dataset.volet);
  });

  // colonnes : les noms de colonnes que l'explorateur sait montrer, remplis quand les données arrivent.
  return { fr, part, id, html, svg, survolable, table, compter, placer, dire, entendre, volet, colonnes: new Set() };
})();
