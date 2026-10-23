"""Aperçu autonome des personnages et offres HGSS, consultable hors ligne."""

import html
import json
from pathlib import Path

from .character_curation_hgss import service_name


def write_character_review(folder: Path, catalog: dict) -> None:
    actors = [a for a in catalog["actors"] if a["useful"]]
    payload = dict(
        actors=actors,
        trainers=catalog["trainers"],
        offers=catalog["service_steps"],
        calendar=catalog["calendar"],
        names=catalog["names"],
        items=catalog["field_items"],
        labels={o["command"]: service_name(o["command"]) for o in catalog["service_steps"]},
        services=catalog["services"],
        shops=catalog["shops"],
        tutors=catalog["tutors"],
        trades=catalog["trades"],
        apricorns=catalog["apricorns"],
        athlete_shops=catalog["athlete_shops"],
    )
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    (folder / "index.html").write_text(_PAGE.replace("__DATA__", data), encoding="utf-8")
    for actor in actors:
        if not html.escape(actor["name_fr"]):
            raise ValueError("HGSS : personnage sans libellé dans l'aperçu")


_PAGE = """<!doctype html><html lang="fr"><meta charset="utf-8">
<title>Pokémaps — Personnages et services HGSS</title>
<style>
body{font:16px system-ui;background:#f3f5f8;color:#172237;margin:24px}
h1{margin-bottom:8px}input{padding:12px;width:min(90%,640px);font:inherit}
nav{display:flex;gap:16px;margin:20px 0}a{color:#164b90}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px}
article,details{background:white;padding:16px;border-radius:12px;border:1px solid #dce2eb}
article img{float:right;image-rendering:pixelated;max-height:80px}small{display:block;color:#42516a}
table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;text-align:left;border:1px solid #ddd}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}section{margin:24px 0}summary{cursor:pointer}
</style><h1>Personnages, objets et services HGSS</h1>
<p>Sources natives épinglées. Les variantes de scénario restent conditionnelles.</p>
<nav><a href="#actors">Personnages</a><a href="#calendar">Revanches</a><a href="#offers">Offres</a>
<a href="#items">Objets placés</a><a href="#services">Catalogues de services</a></nav>
<input id="search" type="search" placeholder="Filtrer les personnages par nom ou lieu" aria-label="Rechercher">
<section id="actors"><h2>Personnages</h2><p id="count"></p><div class="grid" id="cards"></div></section>
<section id="calendar"><h2>Pokématos et Ligue</h2><div id="appointments"></div></section>
<section id="offers"><h2>Offres et récompenses</h2><div id="offers-list"></div></section>
<section id="items"><h2>Objets visibles et cachés</h2><div id="items-list"></div></section>
<section id="services"><h2>Catalogues et étapes</h2><div id="service-list"></div></section>
<script>
const data=__DATA__;
const el=id=>document.getElementById(id);
const text=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n};
const teams=new Map(data.trainers.map(t=>[t.id,t]));
function details(title,value){const n=document.createElement('details');n.append(text('summary',title));
n.append(text('pre',JSON.stringify(value,null,2)));return n}
function render(){const q=el('search').value.toLocaleLowerCase('fr');el('cards').replaceChildren();let count=0;
for(const a of data.actors){if(!(a.name_fr+' '+a.place_fr).toLocaleLowerCase('fr').includes(q))continue;
const card=document.createElement('article');const img=document.createElement('img');
img.src='sprites/'+a.native.sprite+'.png';img.alt=a.name_fr;card.append(img,text('h3',a.name_fr));
card.append(text('p',a.place_fr),text('small','Lieu '+a.header+' · acteur '+a.event));
const link=text('a','Voir le placement sur la carte');link.href=a.review_image;card.append(link);
for(const id of a.trainers){const t=teams.get(id);card.append(text('p',t.native_name+' : '+t.party.map(
p=>data.names.species[p.species]+' niv. '+p.level).join(', ')))}
card.append(details('Placement, conditions et provenance',a));el('cards').append(card);count++}
el('count').textContent=count+' personnages affichés';}
el('search').addEventListener('input',render);render();
for(const a of data.calendar.entries){
el('appointments').append(details(a.name_fr+' — '+a.weekday_fr+' · '+a.period_fr,a))}
for(const a of data.calendar.league){el('appointments').append(details('Ligue — '+teams.get(a.initial).name_fr,a))}
for(const o of data.offers){let label=data.labels[o.command];
if(['offer_item','GiveItem'].includes(o.command)&&o.values.length===2)
label+=' — '+(data.names.items[o.values[0]]||o.values[0])+' × '+o.values[1];
el('offers-list').append(details(label+' · banque '+o.bank,o))}
for(const o of data.items){el('items-list').append(details((data.names.items[o.item.item]||'Objet variable')+
' × '+(o.item.quantity||'?')+' — '+o.place_fr,o))}
for(const key of ['services','shops','tutors','trades','apricorns','athlete_shops']){
el('service-list').append(details({services:'Étapes et services',shops:'Boutiques',tutors:'Tuteurs',
trades:'Échanges',apricorns:'Noigrumes',athlete_shops:'Pokéathlon et Cartes Mémo'}[key],data[key]))}
</script></html>
"""
