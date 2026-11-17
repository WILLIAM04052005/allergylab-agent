// Le volet de droite : la conversation avec l'agent.
(() => {
  const { fr, id, html, compter, dire, entendre, volet, colonnes } = window.AL;
  const formulaire = id("formulaire");
  const champ = id("question");
  const bouton = id("envoyer");
  const fil = id("fil");
  const EXEMPLES = ["Quel est l'âge moyen des patients ?", "Quelle proportion de patients vit en zone urbaine ?"];
  const LIBELLES = { reponse: "Réponse", abstention: "Ne peut pas conclure", erreur: "Erreur" };
  const session = { questions: 0, cout: 0, duree: 0 };
  let piste = null; // la question que suggère le dernier choix fait dans les données

  const bas = () => { fil.scrollTop = fil.scrollHeight; };

  // Le champ grandit avec le texte, jusqu'à la hauteur fixée dans la feuille de style.
  function ajuster() {
    champ.style.height = "auto";
    champ.style.height = `${champ.scrollHeight}px`;
  }

  // Une question préparée (un exemple, un plot, une barre) arrive dans le champ, sans partir :
  // l'envoyer coûte un appel au modèle, c'est donc à la personne de le décider.
  function proposer(texte) {
    volet("agent");
    champ.value = texte;
    ajuster();
    champ.focus();
    const cadre = champ.parentElement;
    cadre.classList.remove("propose");
    void cadre.offsetWidth; // relance l'éclat si une question vient d'être proposée
    cadre.classList.add("propose");
  }

  // --- Les questions suggérées, au-dessus du champ : celle du contexte d'abord, puis deux exemples. ---
  function pistes() {
    const suggestions = [...(piste ? [[piste, "piste-question contexte"]] : []), ...EXEMPLES.map((exemple) => [exemple, "piste-question"])];
    id("pistes").replaceChildren(...suggestions.map(([texte, classe]) => {
      const suggestion = html("button", classe, texte);
      suggestion.type = "button";
      suggestion.addEventListener("click", () => proposer(texte));
      return suggestion;
    }));
  }

  // --- Les colonnes que cite une réponse : un clic les ouvre dans les données. ---
  function colonnesCitees(trace, reponse) {
    const texte = [reponse.justification || "", ...(trace.etapes || []).map((etape) => etape.code || "")].join(" ");
    return [...colonnes].filter((nom) => {
      const motif = nom.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      // Le nom entier : « Cor_a_1 » ne doit pas être reconnu dans « Cor_a_1.0101 » ni dans « Cor_a_11 ».
      return new RegExp(`(?<![\\w.])${motif}(?![\\w+]|\\.\\d)`).test(texte);
    }).slice(0, 3);
  }

  function mesure(liste, nom, valeur) {
    const bloc = html("div");
    bloc.append(html("dt", "", nom), html("dd", "", valeur));
    liste.append(bloc);
  }

  // --- La fiche d'une réponse : le statut en toutes lettres, la valeur, la justification, puis les preuves. ---
  // vivante : la réponse vient d'arriver, sa valeur défile ; sinon elle est relue dans l'historique.
  function fiche(trace, vivante) {
    const reponse = trace.reponse && typeof trace.reponse === "object" ? trace.reponse : {};
    const sorte = trace.erreur ? "erreur" : reponse.statut === "abstention" ? "abstention" : "reponse";
    const article = html("article", `fiche ${sorte}`);
    article.append(html("p", "statut", LIBELLES[sorte]));
    if (sorte === "erreur") {
      article.append(html("p", "", trace.erreur));
    } else {
      if (sorte === "reponse" && typeof reponse.valeur === "number") {
        const decimales = Math.min(4, (String(reponse.valeur).split(".")[1] || "").length);
        const valeur = html("p", "valeur", fr(reponse.valeur, decimales));
        if (vivante) compter(valeur, 0, reponse.valeur, (n) => fr(n, decimales));
        article.append(valeur);
      } else if (sorte === "reponse") {
        const texte = String(reponse.valeur);
        article.append(html("p", texte.length > 14 ? "valeur longue" : "valeur", texte));
      }
      article.append(html("p", "", reponse.justification));
    }
    if (trace.jetons) {
      const mesures = html("dl", "mesures");
      mesure(mesures, "Étapes", fr((trace.etapes || []).length));
      mesure(mesures, "Jetons", fr(trace.jetons.entree + trace.jetons.sortie));
      mesure(mesures, "Coût estimé", `${fr(trace.cout_estime || 0, 4)} $`);
      mesure(mesures, "Durée", `${fr(trace.duree_s || 0, 1)} s`);
      article.append(mesures);
    }
    const citees = sorte === "erreur" ? [] : colonnesCitees(trace, reponse);
    if (citees.length) {
      const liens = html("div", "liens");
      for (const nom of citees) {
        const lien = html("button", "lien", "Voir ");
        lien.type = "button";
        lien.append(html("code", "", nom), document.createTextNode(" dans les données"));
        lien.addEventListener("click", () => dire("montrer", nom));
        liens.append(lien);
      }
      article.append(liens);
    }
    if (trace.etapes && trace.etapes.length) {
      const details = html("details");
      details.append(html("summary", "", "Voir les étapes de l'agent"));
      const liste = html("ol");
      for (const etape of trace.etapes) {
        const item = html("li");
        item.append(html("pre", "", etape.code || "(aucun code)"), html("pre", "resultat", etape.resultat || ""));
        liste.append(item);
      }
      details.append(liste);
      article.append(details);
    }
    if (trace.trace) article.append(html("p", "chemin", `Trace : ${trace.trace}`));
    return article;
  }

  // --- Pendant que l'agent travaille : une puce qui clignote, et ses étapes à mesure qu'il les finit. ---
  function attente() {
    const noeud = html("div", "attente");
    const tete = html("div", "attente-tete");
    const points = html("span", "puce");
    points.setAttribute("aria-hidden", "true");
    for (let i = 0; i < 16; i++) {
      const plot = html("i");
      plot.style.animationDelay = `${(Math.random() * 1.6).toFixed(2)}s`;
      points.append(plot);
    }
    const texte = html("span");
    tete.append(points, texte);
    const liste = html("ol", "vives");
    noeud.append(tete, liste);

    const debut = Date.now();
    let vues = 0;
    let jetons = 0;
    const tic = () => {
      texte.textContent = `L'agent travaille depuis ${Math.round((Date.now() - debut) / 1000)} s${jetons ? `, ${fr(jetons)} jetons` : ""}`;
    };
    const suivre = (etat) => {
      jetons = etat.jetons.entree + etat.jetons.sortie;
      for (const code of etat.etapes.slice(vues)) {
        vues += 1;
        const item = html("li");
        // La première ligne du code suffit à dire ce que l'étape a fait.
        item.append(html("span", "", `Étape ${vues}`), html("code", "", (code || "").split("\n").find((ligne) => ligne.trim()) || "…"));
        liste.append(item);
      }
      tic();
      bas();
    };
    tic();
    return { noeud, tic, suivre };
  }

  // --- Les totaux de la session, en tête du volet : la frugalité se lit sans calcul. ---
  function compterSession(trace) {
    const avant = { ...session };
    session.questions += 1;
    session.cout += trace.cout_estime || 0;
    session.duree += trace.duree_s || 0;
    compter(id("session-questions"), avant.questions, session.questions, (n) => fr(Math.round(n)));
    compter(id("session-cout"), avant.cout, session.cout, (n) => `${fr(n, 4)} $`);
    compter(id("session-duree"), avant.questions ? avant.duree / avant.questions : 0, session.duree / session.questions, (n) => `${fr(n, 1)} s`);
  }

  async function poser(question) {
    bouton.disabled = true;
    id("accueil").hidden = true;
    fil.append(html("p", "demande", question));
    const enCours = attente();
    fil.append(enCours.noeud);
    bas();
    const horloge = setInterval(enCours.tic, 1000);
    const suivi = setInterval(async () => {
      try {
        const etat = await (await fetch("/progression")).json();
        if (etat.en_cours) enCours.suivre(etat);
      } catch { /* le suivi est un confort : la réponse arrivera de toute façon */ }
    }, 700);

    let trace;
    try {
      const retour = await fetch("/question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      trace = await retour.json();
    } catch {
      trace = { erreur: "Le serveur ne répond pas. Vérifiez qu'il tourne encore dans son terminal, puis reposez la question." };
    }
    clearInterval(horloge);
    clearInterval(suivi);
    enCours.noeud.remove();
    fil.append(fiche(trace, true));
    bas();
    if (trace.jetons) compterSession(trace);
    bouton.disabled = false;
    champ.focus();
  }

  formulaire.addEventListener("submit", (evenement) => {
    evenement.preventDefault();
    const question = champ.value.trim();
    if (!question || bouton.disabled) return;
    champ.value = "";
    ajuster();
    poser(question);
  });

  // Entrée envoie la question ; Maj+Entrée passe à la ligne.
  champ.addEventListener("keydown", (evenement) => {
    if (evenement.key === "Enter" && !evenement.shiftKey) {
      evenement.preventDefault();
      formulaire.requestSubmit();
    }
  });
  champ.addEventListener("input", ajuster);

  entendre("proposer", proposer);
  entendre("piste", (texte) => { piste = texte; pistes(); });
  pistes();

  // Les dernières questions déjà posées, relues dans traces/ : aucun appel au modèle.
  fetch("/historique")
    .then((retour) => retour.json())
    .then((traces) => {
      if (!Array.isArray(traces) || !traces.length) return;
      id("passe-titre").textContent = traces.length > 1 ? `Revoir les ${traces.length} dernières questions` : "Revoir la dernière question";
      for (const trace of traces) id("passe-fil").append(html("p", "demande", trace.question || ""), fiche(trace, false));
      id("passe").hidden = false;
    })
    .catch(() => { /* sans historique, la page marche quand même */ });
})();
