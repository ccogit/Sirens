"""Song-Dramaturgie aus Energie, Transienten und dynamischen Strukturwechseln.

Heuristik, keine behauptete Stimmerkennung oder exakte Harmonieanalyse.
Cues liegen auf geschätzten 4/4-Takten und 4-Takt-Phrasen.
"""
import math


def _mittel(werte, a, b):
    links, rechts = max(0, int(a)), min(len(werte), int(b))
    if rechts <= links:
        return 0.0
    return sum(werte[links:rechts]) / (rechts - links)


def _skalieren(werte):
    if not werte:
        return []
    sortiert = sorted(werte)
    p90 = sortiert[min(len(sortiert)-1, int(len(sortiert)*0.90))]
    return [min(1.0, max(0.0, v / max(1, p90))) for v in werte]


def analyse_abschnitte(energie, transienten, brillanz, bpm, bar0, dauer, hz=100):
    """Strukturelle Bogenform und Eingangs-/Ausgangscues für das automatische Set."""
    if bpm <= 0 or dauer <= 0:
        return {"timeline": [], "cues_in": [], "cues_out": [], "phrase_confidence": 0.0}
    takt = 240.0 / bpm
    erstes = bar0 % takt
    # Bildet die gefühlte Energie je Takt ab: Nachbarabschnitte statt Einzelspitzen.
    n = min(400, max(0, int((dauer - erstes) / takt)))
    if n < 8:
        return {"timeline": [], "cues_in": [], "cues_out": [], "phrase_confidence": 0.0}
    e, p, h = [], [], []
    for i in range(n):
        beginn = round((erstes + i*takt) * hz)
        ende = round((erstes + (i+1)*takt) * hz)
        e.append(_mittel(energie, beginn, ende))
        p.append(_mittel(transienten, beginn, ende))
        h.append(_mittel(brillanz, beginn, ende))
    e = _skalieren(e)
    p = _skalieren(p)
    h = _skalieren(h)

    def delta(i):
        vorher = _mittel(e, i-4, i)
        nachher = _mittel(e, i, i+4)
        return nachher - vorher

    def beschreibung(i):
        a = delta(i)
        if a > 0.25: return "Aufbau / Energieanstieg"
        if a < -0.25: return "Break / Energieabfall"
        if _mittel(e, i, i+2) < 0.32: return "ruhiger Abschnitt"
        if _mittel(e, i, i+2) > 0.75: return "energiegeladene Passage"
        return "stabiler Groove"

    # 4-Takt-Downbeats sind nur angenäherte Phrasengrenzen;
    # ohne strukturelle Features wird das nicht als sicher dargestellt.
    kandidaten = list(range(0,n,4))
    raus, rein = [], []
    for i in kandidaten:
        zeit = round(erstes + i*takt, 2)
        energie_vor = _mittel(e, i-4, i)
        energie_nach = _mittel(e, i, i+4)
        perk = _mittel(p, i, i+4)
        bruch = max(0.0, energie_vor-energie_nach)
        aufbau = max(0.0, energie_nach-energie_vor)
        struktur = abs(energie_vor-energie_nach)
        # Frühestens nach einer halben Minute, bevorzugt nach einem Höhepunkt
        # und vor dem Fade-Out/Ende; Peaks und Breaks sind stärkere Übergangsstellen.
        if zeit >= max(24, dauer*0.34) and zeit <= dauer - takt*2:
            spaet = min(1.0, max(0.0, (zeit/dauer-0.30)/0.64))
            score = 0.18*(1-energie_nach)+0.31*bruch+0.22*struktur+0.19*spaet+0.10*(1-perk)
            raus.append({"zeit":zeit, "score":round(min(1,score),3),
                         "energie":round(energie_nach,2), "grund":beschreibung(i),
                         "takt":i+1})
        # Einleitungen, Breaks und neue Energieeintritte sind mögliche Startcues.
        if zeit <= min(dauer*0.48, 120) and zeit < dauer-16:
            frueh = max(0.0, 1-zeit/max(30,min(dauer*.48,120)))
            score = 0.20*(1-energie_vor)+0.30*aufbau+0.18*struktur+0.14*frueh+0.18*perk
            rein.append({"zeit":zeit, "score":round(min(1,score),3),
                         "energie":round(energie_nach,2), "grund":beschreibung(i),
                         "takt":i+1})
    # Nützliche Cue-Alternativen, keine Duplikate innerhalb von 4 Takten.
    raus.sort(key=lambda c:c["score"],reverse=True)
    rein.sort(key=lambda c:c["score"],reverse=True)
    # Eine verlässliche Basis mit dem Einstieg nahe Beginn, selbst bei wenig Struktur.
    if not rein: rein.append({"zeit":round(erstes,2),"score":0.1,
                             "energie":round(e[0],2),"grund":"Songanfang","takt":1})
    timeline = [
        {"zeit":round(erstes+i*takt,1), "energie":round(_mittel(e,i,i+4),2),
         "impuls":round(_mittel(p,i,i+4),2),"helligkeit":round(_mittel(h,i,i+4),2),
         "phase":beschreibung(i)}
        for i in range(0,n,4)
    ]
    kontraste = [abs(delta(i)) for i in kandidaten if i>=4 and i<n-4]
    phrase_confidence = round(min(0.9,max(.12,0.25+sum(kontraste)/max(1,len(kontraste))*.8)),2)
    return {"timeline":timeline[:90], "cues_in":rein[:8],
            "cues_out":raus[:12], "phrase_confidence":phrase_confidence}


def _preis(cue_a,cue_b,match,bars):
    # Paarwert: strukturell sinnvolle Ausgangs-/Einstiegsphasen,
    # energetische Kohärenz und moderater Tempo-Eingriff.
    energie = 1 - abs(cue_a["energie"] - cue_b["energie"])
    leise = 1 - (cue_a["energie"] + cue_b["energie"])/2
    return (.30*cue_a["score"]+.32*cue_b["score"]+.20*energie+.10*leise
            +.08*max(0,1-match["abweichung"]*5))


def paar_uebergang(a,b,bars=8,jetzt=0,rate_min=.84,rate_max=1.19):
    """Berechnet das beste dramaturgische Cue-Paar und die natürliche Übergangszeit."""
    from math import log
    if not a or not b or a.get("bpm",0)<=0 or b.get("bpm",0)<=0:
        return None
    x=a["bpm"]
    moeglich=[b["bpm"]*.5,b["bpm"],b["bpm"]*2]
    norm=min(moeglich,key=lambda v:abs(log(v/x)))
    rate=x/norm
    if not rate_min<=rate<=rate_max: return None
    sekunden=bars*240/x
    aus=a.get("cues_out") or []
    ein=b.get("cues_in") or []
    if not aus or not ein: return None
    beste=None
    for ca in aus:
        if ca["zeit"]<=jetzt+max(2,sekunden*.65):
            continue
        if ca["zeit"]+sekunden >= a.get("duration",float("inf"))-0.5:
            continue
        for cb in ein:
            wert=_preis(ca,cb,{"abweichung":abs(log(rate))},bars)
            if beste is None or wert>beste["score"]:
                beste={"start_a":ca["zeit"],"start_b":cb["zeit"],"rate_b":round(rate,5),
                       "bpm":round(x,2),"bars":bars,"seconds":round(sekunden,2),
                       "score":round(wert,3),"ausgang":ca["grund"],
                       "eingang":cb["grund"],"confidence":round(min(
                           a.get("confidence",0), b.get("confidence",0),
                           a.get("phrase_confidence",0),b.get("phrase_confidence",0)),2)}
    return beste
