"""Conductor de pruebas del Organizador Princess en Linux (Xvfb).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Arranca main_agenda.py de verdad (Tkinter + ttkbootstrap) con lo propio de Windows simulado y ejecuta
pasos dentro del bucle de Tkinter: capturas, árbol de widgets, clics (invoke) y escritura en campos.
Uso: python conductor.py <raíz organizador> <carpeta salida> <archivo de pasos .py>
El archivo de pasos define PASOS = [(nombre, función(c), espera_ms), ...].
"""
import ctypes
import faulthandler
faulthandler.enable(all_threads=True)
import os
import subprocess
import sys
import threading
import time
import traceback
from unittest import mock

RAIZ, SALIDA, PASOS_PY = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(SALIDA, exist_ok=True)

# ── Windows simulado ────────────────────────────────────────────────────────
ctypes.windll = mock.MagicMock()
ctypes.windll.kernel32.GetLastError.return_value = 0
ctypes.WinDLL = mock.MagicMock()
sys.modules["winsound"] = mock.MagicMock()
ABIERTOS = []
os.startfile = lambda ruta, *a, **k: ABIERTOS.append(str(ruta))
def _sin_login():
    raise OSError("sin consola")
os.getlogin = _sin_login

ERRORES = []
REGISTRO = open(os.path.join(SALIDA, "conductor.log"), "w", encoding="utf-8")


def log(msg):
    linea = time.strftime("%H:%M:%S ") + msg
    print(linea, flush=True)
    REGISTRO.write(linea + "\n")
    REGISTRO.flush()


_hook_original = threading.excepthook
def _hook_hilos(args):
    ERRORES.append(f"[hilo {args.thread.name}] {args.exc_type.__name__}: {args.exc_value}")
    log("EXCEPCIÓN EN HILO " + "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))
threading.excepthook = _hook_hilos

import tkinter as tk  # noqa: E402
import tkinter.messagebox as _mb  # noqa: E402
import tkinter.filedialog as _fd  # noqa: E402
MENSAJES = []
RESPUESTAS = {"askyesno": True, "askokcancel": True, "askyesnocancel": True, "askquestion": "yes", "askretrycancel": False}
def _falso_mb(tipo):
    def f(title=None, message=None, **kw):
        MENSAJES.append((tipo, str(title), str(message)))
        log(f"[messagebox.{tipo}] {title}: {str(message)[:300]!r}")
        return RESPUESTAS.get(tipo, "ok")
    return f
for _t in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askyesnocancel", "askquestion", "askretrycancel"):
    setattr(_mb, _t, _falso_mb(_t))
ARCHIVOS = {"guardar": None, "abrir": None, "carpeta": None}
def _falso_fd(clave):
    def f(*a, **kw):
        log(f"[filedialog.{clave}] {kw.get('title', '')!r} → {ARCHIVOS[clave]!r}")
        return ARCHIVOS[clave] or ""
    return f
_fd.asksaveasfilename = _falso_fd("guardar"); _fd.askopenfilename = _falso_fd("abrir"); _fd.askdirectory = _falso_fd("carpeta")
_rce_original = tk.Tk.report_callback_exception
def _rce(self, exc, val, tb):
    ERRORES.append(f"[tk] {exc.__name__}: {val}")
    log("EXCEPCIÓN EN CALLBACK " + "".join(traceback.format_exception(exc, val, tb)))
tk.Tk.report_callback_exception = _rce


class Conductor:
    def __init__(self, app, g):
        self.app, self.g = app, g
        self.n = 0
        self.resultados = []

    # ── utilidades ──
    def captura(self, nombre):
        self.app.update_idletasks(); self.app.update()
        self.n += 1
        ruta = os.path.join(SALIDA, f"{self.n:02d}_{nombre}.png")
        subprocess.run(["import", "-window", "root", ruta], check=False)
        log(f"captura {os.path.basename(ruta)}")
        return ruta

    def ventanas(self):
        out = []
        def rec(w):
            for h in w.winfo_children():
                if isinstance(h, tk.Toplevel):
                    out.append(h)
                rec(h)
        rec(self.app)
        return [v for v in out if v.winfo_exists()]

    def ventana(self, contiene):
        for v in self.ventanas():
            try:
                if contiene.lower() in v.title().lower():
                    return v
            except tk.TclError:
                pass
        return None

    def titulos(self):
        r = []
        for v in self.ventanas():
            try:
                r.append(v.title())
            except tk.TclError:
                pass
        return r

    def widgets(self, raiz):
        out = []
        def rec(w):
            out.append(w)
            for h in w.winfo_children():
                rec(h)
        rec(raiz)
        return out

    @staticmethod
    def texto(w):
        try:
            if w.winfo_class() == "Text":
                return w.get("1.0", "end").strip()
            if w.winfo_class() == "Canvas":
                partes = []
                for it in w.find_all():
                    try:
                        if w.type(it) == "text":
                            partes.append(str(w.itemcget(it, "text")))
                    except tk.TclError:
                        pass
                return " ".join(partes)
        except tk.TclError:
            pass
        for op in ("text", "label"):
            try:
                t = w.cget(op)
                if t:
                    return str(t)
            except (tk.TclError, ValueError):
                pass
        return ""

    def boton(self, raiz, contiene):
        for w in self.widgets(raiz):
            if hasattr(w, "invoke") and contiene.lower() in self.texto(w).lower():
                return w
        return None

    def pulsar(self, raiz, contiene):
        b = self.boton(raiz, contiene)
        if b is None:
            raise AssertionError(f"no hay botón «{contiene}» en {getattr(raiz, 'title', lambda: '?')()}")
        log(f"pulsar «{self.texto(b).strip()}»")
        b.invoke()
        return b

    def entradas(self, raiz):
        return [w for w in self.widgets(raiz) if w.winfo_class() in ("TEntry", "Entry", "TCombobox", "TSpinbox")]

    def escribir(self, w, texto):
        w.delete(0, "end"); w.insert(0, texto)

    def arbol(self, raiz, nombre):
        ruta = os.path.join(SALIDA, f"arbol_{nombre}.txt")
        with open(ruta, "w", encoding="utf-8") as f:
            def rec(w, n=0):
                extra = ""
                try:
                    if w.winfo_class() in ("TEntry", "Entry", "TCombobox"):
                        oculto = bool(w.cget("show")) if w.winfo_class() != "TCombobox" else False
                        extra = f" valor={'«oculto»' if oculto else repr(w.get())} show={w.cget('show')!r}"
                except tk.TclError:
                    pass
                f.write("  " * n + f"{w.winfo_class()} {self.texto(w)!r}{extra}\n")
                for h in w.winfo_children():
                    rec(h, n + 1)
            rec(raiz)
        log(f"árbol {os.path.basename(ruta)}")

    def cerrar(self, v):
        """Cierra como el botón ✕ de la ventana: usa su WM_DELETE_WINDOW si lo tiene."""
        if v is None or not v.winfo_exists():
            return
        try:
            cmd = v.protocol("WM_DELETE_WINDOW")
        except tk.TclError:
            cmd = ""
        if cmd:
            v.tk.call(cmd)
            if v.winfo_exists():
                v.destroy()
        else:
            v.destroy()

    def ok(self, nombre, cond, det=""):
        self.resultados.append((nombre, bool(cond), det))
        log(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
        return cond


ESTADO_CONDUCTOR = {"c": None, "ns": None}


def _resumen_y_salir():
    c = ESTADO_CONDUCTOR["c"]
    log("── FIN ──")
    ok = sum(1 for r in c.resultados if r[1]); mal = [r for r in c.resultados if not r[1]]
    log(f"RESUMEN: {ok} OK, {len(mal)} fallos, {len(ERRORES)} excepciones")
    for r in mal:
        log(f"  FALLO: {r[0]} → {r[2]}")
    for e in ERRORES:
        log(f"  EXCEPCIÓN: {e}")
    REGISTRO.close()
    os._exit(0)


def _ejecutar(c, pasos, i=0):
    if i >= len(pasos):
        _resumen_y_salir()
    nombre, fn, espera = pasos[i]
    log(f"▶ {nombre}")
    # El siguiente paso se programa ANTES: si fn abre una ventana modal (wait_window),
    # el bucle anidado de Tkinter sigue ejecutando los temporizadores.
    c.app.after(espera, lambda: _ejecutar(c, pasos, i + 1))
    try:
        fn(c)
    except Exception as e:  # noqa: BLE001
        ERRORES.append(f"[paso {nombre}] {type(e).__name__}: {e}")
        log(f"ERROR en paso {nombre}: " + traceback.format_exc())


_mainloop_original = tk.Misc.mainloop
def _mainloop(self, n=0):
    g = sys._getframe(1).f_globals
    pasos_ns = {"__name__": "pasos", "log": log, "ABIERTOS": ABIERTOS, "ERRORES": ERRORES, "tk": tk,
                "MENSAJES": MENSAJES, "ARCHIVOS": ARCHIVOS, "RESPUESTAS": RESPUESTAS, "SALIDA": SALIDA}
    exec(compile(open(PASOS_PY, encoding="utf-8").read(), PASOS_PY, "exec"), pasos_ns)
    c = Conductor(self, g)
    pasos_ns["C"] = c
    ESTADO_CONDUCTOR["c"], ESTADO_CONDUCTOR["ns"] = c, pasos_ns
    self.after(pasos_ns.get("ESPERA_INICIAL", 6000), lambda: _ejecutar(c, pasos_ns["PASOS"]))
    return _mainloop_original(self, n)
tk.Misc.mainloop = _mainloop

os.chdir(RAIZ)
sys.path.insert(0, RAIZ)
sys.argv = [os.path.join(RAIZ, "main_agenda.py")]
import runpy  # noqa: E402
try:
    runpy.run_path("main_agenda.py", run_name="__main__")
except SystemExit:
    pass
# La aplicación se ha cerrado sola (p. ej. al importar una configuración, que la cierra a propósito)
if ESTADO_CONDUCTOR["c"] is not None:
    log("la aplicación se ha cerrado")
    al_cerrar = ESTADO_CONDUCTOR["ns"].get("AL_CERRAR")
    if al_cerrar:
        try:
            al_cerrar(ESTADO_CONDUCTOR["c"])
        except Exception as e:  # noqa: BLE001
            ERRORES.append(f"[al cerrar] {type(e).__name__}: {e}")
    _resumen_y_salir()
