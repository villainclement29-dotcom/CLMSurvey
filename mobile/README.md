# Veille — coquille iOS (Capacitor)

Ce dossier contient uniquement une coquille native : elle ouvre directement
`https://clmsurvey.vercel.app` dans une WebView, sans copie locale du site.
Toute la logique reste sur le serveur — mettre à jour le site en production
suffit, pas besoin de reconstruire l'app pour un changement de contenu/CSS.
Seuls l'icône, le nom, l'orientation ou l'ajout d'une capacité native
(biométrie, notifications natives...) demanderaient de reconstruire.

## Ce qui est déjà fait

- Projet Capacitor initialisé (`capacitor.config.json`), pointé vers le site
  en production.
- Plateforme iOS ajoutée (`ios/App`), Swift Package Manager (pas besoin de
  CocoaPods/`pod install`).
- Icône générée à partir de `app/static/icons/icon-512.png` (fond aplati en
  `#0f1115`, sans transparence — obligatoire pour une icône iOS).
- Orientation verrouillée en portrait (le site n'a jamais été pensé pour le
  paysage).

Non testé : la compilation elle-même. Xcode (l'application complète, pas
seulement les outils en ligne de commande) n'est pas installé sur cette
machine, et l'installer nécessite ta connexion à l'App Store — c'est donc à
toi de le faire.

## Limite connue : les notifications

Le bouton cloche du calendrier utilise les Web Push standards du
navigateur. Cette API n'est disponible que dans Safari ou une PWA installée
depuis Safari — pas dans une WebView générique comme celle de cette
coquille Capacitor. Le bouton risque donc de ne rien faire (ou d'échouer
silencieusement) une fois sideloadé de cette façon. Pour de vraies
notifications natives ici, il faudrait ajouter le plugin
`@capacitor/push-notifications` et une configuration APNs côté Apple — un
chantier à part, pas fait pour l'instant.

Les liens externes (source des articles, sur des dizaines de domaines
différents) sont en revanche déjà configurés pour s'ouvrir correctement
(`allowNavigation` dans `capacitor.config.json`).

## Étapes restantes (à faire toi-même)

### 1. Installer Xcode
Depuis le Mac App Store (gratuit, ~15 Go). Lance-le une première fois pour
qu'il termine l'installation des composants additionnels.

### 2. Ouvrir le projet
```bash
open ios/App/App.xcodeproj
```
Xcode va résoudre les dépendances Swift Package Manager automatiquement
(barre de progression en haut) — patiente que ça termine avant de continuer.

### 3. Signer avec ton Apple ID
Xcode → Settings (⌘,) → Accounts → "+" → connecte-toi avec ton Apple ID
(gratuit, pas besoin du compte développeur payant pour un sideload perso).

Puis dans le projet : sélectionne la cible "App" → onglet "Signing &
Capabilities" → coche "Automatically manage signing" → choisis ton compte
dans "Team".

### 4. Lancer sur ton iPhone
Branche l'iPhone en câble, déverrouille-le et autorise l'ordinateur si
demandé. En haut de Xcode, choisis ton iPhone comme cible (au lieu d'un
simulateur), puis clique sur ▶️ (Run).

Au premier lancement, iOS refuse l'app tant qu'elle n'est pas approuvée :
sur l'iPhone, Réglages → Général → VPN et gestion de l'appareil → sélectionne
ton compte Apple → "Faire confiance".

**Limite du compte gratuit** : l'app expire au bout de 7 jours (message
"app introuvable" à l'ouverture) — il faut relancer depuis Xcode pour la
resigner. Voir l'étape 5 pour éviter ça.

### 5. AltStore (éviter de repasser par Xcode tous les 7 jours)

1. Installe **AltServer** sur ton Mac : https://altstore.io
2. Lance AltServer (icône dans la barre de menu macOS), connecte l'iPhone en
   câble une première fois, puis dans le menu AltServer : "Install AltStore"
   → choisis ton iPhone → entre ton Apple ID (uniquement demandé par
   AltServer, jamais par moi).
3. Sur l'iPhone, l'app AltStore apparaît. Fais-lui confiance comme à
   l'étape 4.
4. Dans AltStore sur l'iPhone : onglet "My Apps" → "+" → sélectionne le
   fichier `.ipa` exporté depuis Xcode (Xcode → Product → Archive → Distribute
   App → "Development" → exporter le `.ipa`), ou directement l'app déjà
   installée si AltStore la détecte.
5. Tant qu'AltServer tourne sur le Mac (et que le Mac et l'iPhone sont sur le
   même Wi-Fi, ou via le plugin Mail pour un renouvellement à distance),
   AltStore renouvelle automatiquement la signature avant l'expiration des
   7 jours — plus besoin de repasser par Xcode à chaque fois.

## Mettre à jour l'app plus tard

- Changement de contenu/style/fonctionnalité côté site : rien à faire ici,
  c'est en ligne dès le déploiement.
- Changement d'icône, de nom, ou ajout d'une capacité native : relancer
  `npx capacitor-assets generate --ios` (icône) et/ou éditer
  `capacitor.config.json`, puis `npx cap sync ios`, puis reconstruire depuis
  Xcode.
