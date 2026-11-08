"""Comprobaciones de estructura del código (sin Windows ni interfaz).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_estructura.py
1. Ningún módulo importa main_agenda: es el script de arranque (__main__) e importarlo vuelve a
   ejecutar la aplicación entera dentro del mismo proceso (v4.18.06).
2. Ninguna lambda usa la variable de un «except ... as X» sin pasarla como argumento: Python borra X
   al salir del bloque y la lambda, que se ejecuta después (after, hilos), da NameError (v4.18.06).
"""
import ast
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
fallos = []

for carpeta, _, ficheros in os.walk(RAIZ):
    if any(p in carpeta for p in (".git", "build", "dist", "__pycache__")):
        continue
    for nombre in ficheros:
        if not nombre.endswith(".py") or nombre == os.path.basename(__file__):
            continue
        ruta = os.path.join(carpeta, nombre)
        rel = os.path.relpath(ruta, RAIZ)
        arbol = ast.parse(open(ruta, encoding="utf-8").read(), rel)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import) and any(a.name == "main_agenda" for a in nodo.names):
                fallos.append(f"{rel}:{nodo.lineno}: import main_agenda")
            if isinstance(nodo, ast.ImportFrom) and nodo.module == "main_agenda":
                fallos.append(f"{rel}:{nodo.lineno}: from main_agenda import ...")
            if isinstance(nodo, ast.ExceptHandler) and nodo.name:
                for sub in ast.walk(nodo):
                    if isinstance(sub, ast.Lambda):
                        params = {a.arg for a in sub.args.args + sub.args.kwonlyargs}
                        usa = any(isinstance(n, ast.Name) and n.id == nodo.name for n in ast.walk(sub.body))
                        if usa and nodo.name not in params:
                            fallos.append(f"{rel}:{sub.lineno}: lambda usa «{nodo.name}» del except sin pasarla como argumento")

if fallos:
    print("FALLOS:")
    for f in fallos:
        print("  " + f)
    sys.exit(1)
print("Estructura OK: nadie importa main_agenda y ninguna lambda usa la variable de un except.")
