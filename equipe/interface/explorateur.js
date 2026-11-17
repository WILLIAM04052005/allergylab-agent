// Le volet de gauche : explorer les données.
// Les chiffres viennent de /donnees (equipe/interface/donnees.py) : aucun appel au modèle.
(() => {
  const { fr, part, id, html, svg, survolable, table, compter, placer, dire, entendre, volet, colonnes } = window.AL;
  const MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  const MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  // La couleur suit la puce, jamais son rang : une puce garde sa couleur quel que soit le filtre.
  const COULEUR = { ISAC_V1: "var(--serie-1)", ISAC_V2: "var(--serie-2)", ALEX: "var(--serie-3)" };
  const ans = (n) => `${fr(n, n % 1 ? 1 : 0)} ans`;

  let donnees = null;
  let puce = "Toutes"; // le filtre
  let vue = "dosages"; // l'onglet ouvert
  let dosage = null; // le dosage détaillé
  let variable = "Gender"; // la variable clinique détaillée
  let piste = null; // la question à suggérer à l'agent, d'après le dernier choix
  let calme = false; // vrai pendant un redessin dû à un changement de largeur : les animations ne sont pas rejouées
  let largeur = 0;

  const tranche = () => donnees.tranches[puce];
  const ou = () => (puce === "Toutes" ? "" : ` sur la puce ${puce}`);
  const anime = (noeud) => noeud.classList.toggle("anime", !calme);

  // --- Les dosages : une part par colonne, ou null quand trop peu de patients sont mesurés. ---
  function partDosage(t, i) {
    const mesures = t.dosages.mesures[i];
    return mesures >= donnees.minimum ? t.dosages.non_nuls[i] / mesures : null;
  }

  // Tous les dosages d'une tranche, du plus souvent au-dessus de zéro au moins souvent ; les non mesurés à la fin.
  function classement(t) {
    return donnees.dosages
      .map((nom, i) => ({ nom, mesures: t.dosages.mesures[i], non_nuls: t.dosages.non_nuls[i], part: partDosage(t, i) }))
      .sort((a, b) => (b.part ?? -1) - (a.part ?? -1));
  }

  // --- Les chiffres clés : au changement de filtre, chaque nombre défile de l'ancienne valeur à la nouvelle. ---
  const compteurs = {};

  function tuiles() {
    const t = tranche();
    const liste = [
      ["patients", "Patients", t.patients, (n) => fr(Math.round(n)), puce === "Toutes" ? "toutes puces confondues" : `testés sur la puce ${puce}`],
      ["age", "Âge médian", t.age.mediane ?? 0, (n) => ans(Math.round(n * 2) / 2), `${fr(t.age.renseignes)} âges connus`],
      ["dosages", "Dosages mesurés", t.dosages.mesures.filter((n) => n >= donnees.minimum).length, (n) => fr(Math.round(n)), `sur ${fr(donnees.dosages.length)} colonnes de dosage`],
    ];
    for (const [cle, nom, cible, ecrire, precision] of liste) {
      if (!compteurs[cle]) {
        const tuile = html("div", "tuile");
        compteurs[cle] = { nombre: html("p", "nombre"), precision: html("p", "precision"), valeur: 0 };
        tuile.append(html("p", "nom", nom), compteurs[cle].nombre, compteurs[cle].precision);
        id("tuiles").append(tuile);
      }
      compteurs[cle].precision.textContent = precision;
      compter(compteurs[cle].nombre, compteurs[cle].valeur, cible, ecrire);
      compteurs[cle].valeur = cible;
    }
  }

  // --- Une ligne de barre : un nom, une barre, un chiffre. ---
  function ligne(nom, precision, proportion, chiffre, options = {}) {
    const titre = html("span", "nom");
    if (options.couleur) {
      const pastille = html("span", "pastille");
      pastille.style.background = options.couleur;
      titre.append(pastille);
    }
    titre.append(html(options.code ? "code" : "span", "", nom));
    if (precision) titre.append(html("small", "", precision));
    const rail = html("span", options.jauge ? "piste jauge" : "piste");
    if (!options.vide) {
      const barre = html("span", "barre");
      barre.style.width = `${100 * proportion}%`;
      barre.style.animationDelay = `${options.delai || 0}ms`;
      if (options.couleur) barre.style.background = options.couleur;
      rail.append(barre);
    }
    return [titre, rail, html("span", "chiffre", chiffre)];
  }

  // ====================== Vue « Dosages » ======================

  // La puce : un plot par dosage, dans l'ordre du fichier. Sa lumière dit la part des patients au-dessus de zéro.
  let plots = null;
  let partMax = 0;

  function scan() {
    const t = tranche();
    const grille = id("plots");
    if (!plots) {
      // La même échelle pour toutes les puces : un plot aussi vif veut dire la même part, quel que soit le filtre.
      partMax = Math.max(...Object.values(donnees.tranches).flatMap((autre) => donnees.dosages.map((_, i) => partDosage(autre, i) ?? 0)));
      plots = donnees.dosages.map((nom) => {
        const plot = html("button", "plot");
        plot.type = "button";
        plot.tabIndex = -1; // 241 arrêts de tabulation seraient pénibles : au clavier, la recherche et le tableau donnent accès à tout
        survolable(plot, () => plot.dataset.valeur, () => plot.dataset.nom);
        plot.addEventListener("click", () => choisirDosage(nom));
        return plot;
      });
      grille.replaceChildren(...plots);
      id("echelle-max").textContent = `${fr(100 * partMax)} %`;
      void grille.offsetWidth; // les plots existent éteints avant de s'allumer : la première lecture se voit aussi
    }
    // Les rangées s'allument l'une après l'autre, de haut en bas, comme passe la lecture d'une puce.
    const parRangee = getComputedStyle(grille).gridTemplateColumns.split(" ").length;
    plots.forEach((plot, i) => {
      const valeur = partDosage(t, i);
      const mesures = t.dosages.mesures[i];
      const nom = donnees.dosages[i];
      plot.style.transitionDelay = calme ? "0ms" : `${Math.floor(i / parRangee) * 40}ms`;
      plot.classList.toggle("absent", valeur === null);
      plot.classList.toggle("choisi", nom === dosage);
      plot.style.setProperty("--v", valeur === null ? 0 : (0.06 + (0.94 * valeur) / partMax).toFixed(3));
      plot.dataset.valeur = valeur === null ? "Non mesuré" : `${part(t.dosages.non_nuls[i], mesures)} au-dessus de zéro`;
      plot.dataset.nom = valeur === null
        ? `${nom} : ${mesures ? `${fr(mesures)} patients mesurés, trop peu pour une part` : "aucun patient mesuré dans cette sélection"}`
        : `${nom} : ${fr(t.dosages.non_nuls[i])} patients sur ${fr(mesures)} mesurés`;
      plot.setAttribute("aria-label", `${plot.dataset.nom}, ${plot.dataset.valeur}`);
    });
    table("plots-table", ["Dosage", "Au-dessus de zéro", "Patients mesurés", "Part"], classement(t).map((d) => (
      d.part === null ? [d.nom, "—", fr(d.mesures), "non mesuré"] : [d.nom, fr(d.non_nuls), fr(d.mesures), part(d.non_nuls, d.mesures)]
    )));
  }

  // La recherche éteint les plots dont le nom ne contient pas le texte tapé ; Entrée ouvre le premier trouvé.
  function trouves() {
    const mot = id("recherche").value.trim().toLowerCase();
    return donnees.dosages.filter((nom) => !mot || nom.toLowerCase().includes(mot));
  }

  function chercher() {
    const mot = id("recherche").value.trim();
    const gardes = new Set(trouves());
    plots.forEach((plot, i) => {
      plot.style.transitionDelay = "0ms";
      plot.classList.toggle("hors", !gardes.has(donnees.dosages[i]));
    });
    id("trouves").textContent = !mot ? "" : gardes.size ? `${gardes.size} dosage${gardes.size > 1 ? "s" : ""} sur ${plots.length}` : "Aucun dosage ne porte ce nom";
  }

  id("recherche").addEventListener("input", chercher);
  id("recherche").addEventListener("keydown", (evenement) => {
    if (evenement.key !== "Enter") return;
    evenement.preventDefault();
    if (id("recherche").value.trim() && trouves().length) choisirDosage(trouves()[0]);
  });

  const questionDosage = () => `Combien de patients ont un dosage ${dosage} au-dessus de zéro${ou()} ?`;

  function choisirDosage(nom) {
    dosage = nom;
    plots.forEach((plot, i) => plot.classList.toggle("choisi", donnees.dosages[i] === nom));
    for (const bouton of id("premiers").querySelectorAll("button")) bouton.setAttribute("aria-pressed", String(bouton.dataset.nom === nom));
    ficheDosage();
    piste = questionDosage;
    dire("piste", piste());
  }

  // La fiche du dosage choisi : sa part dans la sélection, puis la même part sur chacune des trois puces.
  function ficheDosage() {
    const t = tranche();
    const i = donnees.dosages.indexOf(dosage);
    const valeur = partDosage(t, i);
    const mesures = t.dosages.mesures[i];

    const titre = html("h2", "", "Dosage ");
    titre.append(html("code", "", dosage));
    const grand = html("p", "grand");
    if (valeur === null) grand.textContent = "Non mesuré";
    else if (calme) grand.textContent = `${fr(100 * valeur, 1)} %`;
    else compter(grand, 0, 100 * valeur, (n) => `${fr(n, 1)} %`);
    const detail = html("p", "sous-titre", valeur !== null
      ? `${fr(t.dosages.non_nuls[i])} patients au-dessus de zéro, sur ${fr(mesures)} mesurés${ou()}.`
      : mesures ? `${fr(mesures)} patients mesurés${ou()}, trop peu pour calculer une part.` : `Aucun patient mesuré${ou()}.`);
    const resume = html("div");
    resume.append(titre, grand, detail);

    const bouton = html("button", "second", "Demander à l'agent");
    bouton.type = "button";
    bouton.addEventListener("click", () => dire("proposer", questionDosage()));
    const tete = html("div", "fiche-tete");
    tete.append(resume, bouton);

    const liste = html("ul", "barres");
    anime(liste);
    donnees.puces.forEach((p, rang) => {
      const sur = partDosage(donnees.tranches[p.nom], i);
      const item = html("li");
      item.append(...ligne(p.nom, "", sur === null ? 0 : sur / partMax, sur === null ? "non mesuré" : `${fr(100 * sur, 1)} %`, { couleur: COULEUR[p.nom], delai: rang * 70, vide: sur === null }));
      liste.append(item);
    });
    id("fiche-dosage").replaceChildren(tete, html("p", "sous-titre", "La même part, puce par puce :"), liste);
  }

  function premiers() {
    const lignes = classement(tranche()).filter((d) => d.part !== null).slice(0, 10);
    const max = Math.max(...lignes.map((d) => d.part), 0.0001);
    const liste = id("premiers");
    anime(liste);
    liste.replaceChildren(...lignes.map((d, rang) => {
      const bouton = html("button");
      bouton.type = "button";
      bouton.dataset.nom = d.nom;
      bouton.setAttribute("aria-pressed", String(d.nom === dosage));
      bouton.append(...ligne(d.nom, "", d.part / max, part(d.non_nuls, d.mesures), { code: true, delai: rang * 35 }));
      bouton.addEventListener("click", () => choisirDosage(d.nom));
      const item = html("li");
      item.append(bouton);
      return item;
    }));
  }

  // ====================== Vue « Patients » ======================

  // Patients par puce : un tout découpé en trois blocs.
  function puces() {
    const total = donnees.puces.reduce((somme, p) => somme + p.patients, 0);
    const blocs = donnees.puces.map((p) => {
      const bloc = html("div", puce === "Toutes" || puce === p.nom ? "bloc" : "bloc efface", part(p.patients, total));
      bloc.style.flex = `${p.patients} 0 0`;
      bloc.style.background = COULEUR[p.nom];
      survolable(bloc, `${fr(p.patients)} patients (${part(p.patients, total)})`, `Puce ${p.nom}`);
      return bloc;
    });
    anime(id("puces"));
    id("puces").replaceChildren(...blocs);
    // Un bloc trop étroit pour sa part n'affiche rien : le chiffre reste dans la bulle et le tableau.
    for (const bloc of blocs) if (bloc.scrollWidth > bloc.clientWidth) bloc.textContent = "";
    id("puces-legende").replaceChildren(...donnees.puces.map((p) => {
      const item = html("li");
      const pastille = html("span", "pastille");
      pastille.style.background = COULEUR[p.nom];
      item.append(pastille, document.createTextNode(p.nom));
      return item;
    }));
    table("puces-table", ["Puce", "Patients", "Part"], donnees.puces.map((p) => [p.nom, fr(p.patients), part(p.patients, total)]));
  }

  // Le cadre commun aux deux graphiques en SVG : des graduations rondes et une ligne de base.
  function graduations(max) {
    const brut = max / 4;
    const puissance = 10 ** Math.floor(Math.log10(brut || 1));
    const pas = [1, 2, 5, 10].map((multiple) => multiple * puissance).find((valeur) => valeur >= brut);
    const lignes = [0];
    while (lignes[lignes.length - 1] < max) lignes.push(lignes[lignes.length - 1] + pas);
    return lignes;
  }

  function cadre(cible, max) {
    const dessin = id(cible);
    dessin.replaceChildren();
    anime(dessin);
    const large = dessin.clientWidth || 560;
    const marge = { haut: 22, droite: 8, bas: 26, gauche: 44 };
    dessin.setAttribute("viewBox", `0 0 ${large} 210`);
    const lignes = graduations(max);
    const sommet = lignes[lignes.length - 1];
    const y = (valeur) => marge.haut + (210 - marge.haut - marge.bas) * (1 - valeur / sommet);
    for (const valeur of lignes) {
      dessin.append(svg("line", { class: valeur ? "grille" : "axe", x1: marge.gauche, x2: large - marge.droite, y1: y(valeur), y2: y(valeur) }));
      dessin.append(svg("text", { x: marge.gauche - 8, y: y(valeur) + 4, "text-anchor": "end" }, fr(valeur)));
    }
    return { dessin, marge, y, base: y(0), bande: (nombre) => (large - marge.gauche - marge.droite) / nombre };
  }

  // Une zone de survol par classe ou par mois, plus large que la marque : on vise une colonne, pas un trait.
  function cible(c, bande, i) {
    return svg("rect", { class: "cible", x: c.marge.gauche + i * bande, y: c.marge.haut, width: bande, height: c.base - c.marge.haut });
  }

  // Âge : une colonne par classe de cinq ans, qui monte depuis la ligne de base.
  function ages() {
    const age = tranche().age;
    const classes = age.classes;
    const max = Math.max(...classes.map((classe) => classe.patients), 1);
    const c = cadre("ages", max);
    const bande = c.bande(classes.length);
    const epaisseur = Math.min(24, bande - 2);
    const nom = (classe) => (classe.de >= 90 ? "90 ans et plus" : `${classe.de} à ${classe.de + 4} ans`);
    const plusHaute = classes.find((classe) => classe.patients === max);
    classes.forEach((classe, i) => {
      const x = c.marge.gauche + i * bande + (bande - epaisseur) / 2;
      const haut = c.y(classe.patients);
      const rayon = Math.max(0, Math.min(4, c.base - haut, epaisseur / 2));
      // Sommet arrondi, pied carré posé sur la ligne de base.
      const marque = svg("path", { class: "marque-col", d: `M${x},${c.base}V${haut + rayon}Q${x},${haut} ${x + rayon},${haut}H${x + epaisseur - rayon}Q${x + epaisseur},${haut} ${x + epaisseur},${haut + rayon}V${c.base}Z` });
      marque.style.animationDelay = `${i * 22}ms`;
      const zone = cible(c, bande, i);
      survolable(zone, `${fr(classe.patients)} patients`, nom(classe), () => marque.classList.add("survol"), () => marque.classList.remove("survol"));
      c.dessin.append(marque, zone);
      if (classe.de % 10 === 0) c.dessin.append(svg("text", { x: x + epaisseur / 2, y: c.base + 17, "text-anchor": "middle" }, classe.de >= 90 ? "90+" : String(classe.de)));
      if (classe === plusHaute) c.dessin.append(svg("text", { class: "etiquette", x: x + epaisseur / 2, y: haut - 6, "text-anchor": "middle" }, fr(classe.patients)));
    });
    id("ages-titre").textContent = age.mediane === null
      ? "Aucun âge connu dans cette sélection."
      : `Âge médian : ${ans(age.mediane)}, sur ${fr(age.renseignes)} patients dont l'âge est connu. Une colonne par classe de cinq ans.`;
    table("ages-table", ["Classe d'âge", "Patients"], classes.map((classe) => [nom(classe), fr(classe.patients)]));
  }

  // Mois du prélèvement : une courbe sur douze mois, qui se trace de gauche à droite.
  function mois() {
    const valeurs = tranche().mois;
    const max = Math.max(...valeurs, 1);
    const c = cadre("mois", max);
    const bande = c.bande(12);
    const x = (i) => c.marge.gauche + (i + 0.5) * bande;
    const points = valeurs.map((valeur, i) => `${x(i)},${c.y(valeur)}`).join("L");
    c.dessin.append(svg("path", { class: "aire", d: `M${x(0)},${c.base}L${points}L${x(11)},${c.base}Z` }));
    c.dessin.append(svg("path", { class: "courbe", pathLength: 1, d: `M${points}` }));
    const repere = svg("line", { class: "repere", y1: c.marge.haut, y2: c.base });
    c.dessin.append(repere);
    valeurs.forEach((valeur, i) => {
      c.dessin.append(svg("circle", { class: "point", cx: x(i), cy: c.y(valeur), r: 4 }));
      c.dessin.append(svg("text", { x: x(i), y: c.base + 17, "text-anchor": "middle" }, bande >= 40 ? MOIS_COURTS[i] : MOIS[i][0].toUpperCase()));
      if (i === valeurs.indexOf(max)) c.dessin.append(svg("text", { class: "etiquette", x: x(i), y: c.y(valeur) - 10, "text-anchor": "middle" }, fr(valeur)));
    });
    valeurs.forEach((valeur, i) => {
      const zone = cible(c, bande, i);
      survolable(zone, `${fr(valeur)} patients`, `Prélèvements de ${MOIS[i]}`, () => {
        repere.setAttribute("x1", x(i));
        repere.setAttribute("x2", x(i));
        repere.style.visibility = "visible";
      }, () => { repere.style.visibility = "hidden"; });
      c.dessin.append(zone);
    });
    id("mois-titre").textContent = `${fr(valeurs.reduce((somme, valeur) => somme + valeur, 0))} patients dont le mois de prélèvement est connu.`;
    table("mois-table", ["Mois", "Patients"], valeurs.map((valeur, i) => [MOIS[i], fr(valeur)]));
  }

  // Sexe et habitat : deux petites répartitions, comptées comme dans la vue « Clinique ».
  function partages() {
    for (const [nom, colonne] of [["sexe", "Gender"], ["habitat", "Rural_or_urban_area"]]) {
      const v = tranche().variables.find((candidate) => candidate.colonne === colonne);
      const max = Math.max(...v.codes.map((code) => code.patients), 1);
      anime(id(nom));
      id(nom).replaceChildren(...v.codes.map((code, rang) => {
        const item = html("li");
        item.append(...ligne(code.libelle || `Code ${code.code}`, "", code.patients / max, `${fr(code.patients)} (${part(code.patients, v.renseignes)})`, { delai: rang * 70 }));
        return item;
      }));
      id(`${nom}-note`).textContent = `Connu pour ${part(v.renseignes, tranche().patients)} des patients.`;
    }
  }

  // ====================== Vue « Clinique » ======================

  const questionVariable = () => `Quelle est la répartition des patients dans la colonne ${variable}${ou()} ?`;

  // Les variables cliniques : la part renseignée de chacune. Un clic choisit celle dont on détaille la répartition.
  function variables() {
    const t = tranche();
    anime(id("variables"));
    id("variables").replaceChildren(...t.variables.map((v, rang) => {
      const bouton = html("button");
      bouton.type = "button";
      bouton.setAttribute("aria-pressed", String(v.colonne === variable));
      bouton.append(...ligne(v.rubrique, v.colonne, v.renseignes / (t.patients || 1), part(v.renseignes, t.patients), { jauge: true, delai: rang * 35 }));
      bouton.addEventListener("click", () => {
        variable = v.colonne;
        for (const autre of id("variables").querySelectorAll("button")) autre.setAttribute("aria-pressed", String(autre === bouton));
        repartition();
        piste = questionVariable;
        dire("piste", piste());
      });
      const item = html("li");
      item.append(bouton);
      return item;
    }));
  }

  function repartition() {
    const t = tranche();
    const v = t.variables.find((candidate) => candidate.colonne === variable);
    const max = Math.max(...v.codes.map((code) => code.patients), 1);
    id("repartition-titre").textContent = v.rubrique;
    id("repartition-sous-titre").textContent = `${fr(v.renseignes)} patients renseignés sur ${fr(t.patients)}, colonne ${v.colonne}.`;
    anime(id("repartition"));
    id("repartition").replaceChildren(...v.codes.map((code, rang) => {
      const item = html("li");
      item.append(...ligne(code.libelle || "Sans libellé", `code ${code.code}`, code.patients / max, `${fr(code.patients)} (${part(code.patients, v.renseignes)})`, { delai: rang * 35 }));
      return item;
    }));
    id("repartition-renvoi").textContent = `${v.sens} Correspondance avec le dictionnaire officiel : ${v.correspondance}.`
      + (v.plusieurs ? " Un patient peut porter plusieurs codes : la somme des parts peut dépasser 100 %." : "");
  }

  // ====================== La navigation ======================

  function dessinerVue() {
    if (vue === "dosages") { scan(); ficheDosage(); premiers(); }
    if (vue === "patients") { puces(); ages(); mois(); partages(); }
    if (vue === "clinique") { variables(); repartition(); }
  }

  function ouvrir(nom) {
    vue = nom;
    for (const bouton of id("onglets").querySelectorAll("button")) {
      const actif = bouton.dataset.vue === nom;
      bouton.setAttribute("aria-pressed", String(actif));
      if (actif) placer(id("onglets"), bouton);
    }
    for (const section of document.querySelectorAll(".vue")) section.hidden = section.id !== `vue-${nom}`;
    const section = id(`vue-${nom}`);
    section.classList.remove("entre");
    void section.offsetWidth; // relance l'arrivée des blocs
    section.classList.add("entre");
    dessinerVue();
  }

  id("onglets").addEventListener("click", (evenement) => {
    const bouton = evenement.target.closest("button");
    if (bouton && bouton.dataset.vue !== vue) ouvrir(bouton.dataset.vue);
  });

  // Le filtre s'applique à tout : les chiffres clés, la vue ouverte, et la question suggérée à l'agent.
  id("filtre").addEventListener("change", (evenement) => {
    puce = evenement.target.value;
    placer(id("filtre"), evenement.target.nextElementSibling);
    tuiles();
    dessinerVue();
    if (piste) dire("piste", piste());
  });

  // L'agent cite une colonne dans sa réponse : on l'ouvre ici.
  entendre("montrer", (colonne) => {
    volet("donnees");
    if (donnees.dosages.includes(colonne)) {
      ouvrir("dosages");
      choisirDosage(colonne);
      id("fiche-dosage").scrollIntoView({ block: "nearest" });
    } else if (donnees.tranches.Toutes.variables.some((v) => v.colonne === colonne)) {
      variable = colonne;
      ouvrir("clinique");
    } else {
      ouvrir("patients");
    }
  });

  // Quand la largeur change, les graphiques se redessinent à la bonne taille, sans rejouer leurs animations.
  let report;
  new ResizeObserver(() => {
    clearTimeout(report);
    report = setTimeout(() => {
      const actuelle = id("explorateur").clientWidth;
      if (!donnees || !actuelle || actuelle === largeur) return;
      largeur = actuelle;
      calme = true;
      dessinerVue();
      calme = false;
      placer(id("filtre"), id("filtre").querySelector("input:checked").nextElementSibling);
      placer(id("onglets"), id("onglets").querySelector('[aria-pressed="true"]'));
    }, 120);
  }).observe(id("explorateur"));

  fetch("/donnees")
    .then((retour) => retour.json())
    .then((recu) => {
      donnees = recu;
      for (const nom of donnees.dosages) colonnes.add(nom);
      for (const v of donnees.tranches.Toutes.variables) colonnes.add(v.colonne);
      for (const nom of ["Age", "Blood_Month_sample", "Chip_Type"]) colonnes.add(nom);
      dosage = classement(donnees.tranches.Toutes)[0].nom;
      id("etat").hidden = true;
      id("contenu").hidden = false;
      tuiles();
      ouvrir("dosages");
      largeur = id("explorateur").clientWidth; // mesurée une fois la vue dessinée : elle ne déclenche pas de redessin
    })
    .catch((erreur) => {
      console.error(erreur);
      id("etat").textContent = "Les données n'ont pas pu être chargées. Relancez le serveur dans son terminal, puis rechargez la page.";
    });
})();
