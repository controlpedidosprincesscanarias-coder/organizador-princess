"""Comprobaciones antes de compilar y publicar una versión del Organizador Princess.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Lo usa .github/workflows/compilar.yml (y se puede lanzar a mano):

    python compilacion/preparar_release.py [--releases releases.json] [--notas salida.md] [--github-output FICHERO]

- Lee APP_VERSION de main_agenda.py y MyAppVersion de OrganizadorPrincess_Setup.iss y exige que sean
  la misma versión y que el último número sea par.
- Con --releases (lista de etiquetas, una por línea, o el JSON de
  `gh api repos/OWNER/REPO/releases`), falla si ya existe una Release con esa
  misma versión (comparada como números: v4.18.4 = v4.18.04): nunca se pisa una Release existente.
- Con --notas, escribe las novedades de esta versión (primer bloque de release_notes/release_notes.md),
  sin las instrucciones internas «Al publicar».
- Con --github-output, deja version, etiqueta e instalador como salidas del paso de GitHub Actions.
"""
import argparse
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _leer(rel):
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as f:
        return f.read()


def numeros(version):
    return tuple(int(n) for n in re.findall(r"\d+", version))


def version_app():
    m = re.search(r'^APP_VERSION\s*=\s*"v?([\d.]+)"', _leer("main_agenda.py"), re.M)
    if not m:
        raise SystemExit("ERROR: no se encuentra APP_VERSION en main_agenda.py")
    return m.group(1)


def version_iss():
    m = re.search(r'^#define\s+MyAppVersion\s+"([\d.]+)"', _leer("OrganizadorPrincess_Setup.iss"), re.M)
    if not m:
        raise SystemExit("ERROR: no se encuentra MyAppVersion en OrganizadorPrincess_Setup.iss")
    return m.group(1)


def notas_version(version):
    """Primer bloque de release_notes.md (hasta la primera línea '---'), comprobando que es de esta versión."""
    lineas = _leer("release_notes/release_notes.md").splitlines()
    bloque = []
    for l in lineas:
        if l.strip().startswith("---") and bloque:
            break
        bloque.append(l)
    texto = "\n".join(bloque).strip()
    cabecera = next((l for l in bloque if l.strip()), "")
    if numeros(version) not in [numeros(v) for v in re.findall(r"v?(\d+\.\d+\.\d+)", cabecera)]:
        raise SystemExit(f"ERROR: release_notes/release_notes.md no empieza por las novedades de la {version} "
                         f"(primera línea: {cabecera!r})")
    texto = "\n".join(l for l in texto.splitlines() if not l.strip().startswith("**Al publicar"))
    return texto.strip() + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--releases")
    p.add_argument("--notas")
    p.add_argument("--github-output")
    a = p.parse_args()

    v_app, v_iss = version_app(), version_iss()
    if numeros(v_app) != numeros(v_iss):
        raise SystemExit(f"ERROR: APP_VERSION ({v_app}) y MyAppVersion del .iss ({v_iss}) no coinciden")
    if v_app != v_iss:
        raise SystemExit(f"ERROR: escribe la versión igual en los dos sitios (main_agenda.py: {v_app}, .iss: {v_iss})")
    if numeros(v_app)[-1] % 2:
        raise SystemExit(f"ERROR: la versión {v_app} termina en impar; la numeración del Organizador es par")
    print(f"Versión {v_app}: main_agenda.py y .iss coinciden y es par.")

    if a.releases:
        with open(a.releases, encoding="utf-8-sig") as f:
            contenido = f.read().strip()
        if contenido.startswith("["):
            existentes = [r.get("tag_name") or r.get("tagName") or "" for r in json.loads(contenido)]
        else:  # una etiqueta por línea
            existentes = [l.strip() for l in contenido.splitlines() if l.strip()]
        iguales = [t for t in existentes if numeros(t) == numeros(v_app)]
        if iguales:
            raise SystemExit(f"ERROR: ya existe una Release para la versión {v_app} ({', '.join(iguales)}). "
                             "Sube la versión antes de crear otra; las Releases existentes no se tocan.")
        print(f"No hay ninguna Release con la versión {v_app} ({len(existentes)} revisadas).")

    if a.notas:
        with open(a.notas, "w", encoding="utf-8") as f:
            f.write(notas_version(v_app))
        print(f"Notas de la versión escritas en {a.notas}.")

    if a.github_output:
        with open(a.github_output, "a", encoding="utf-8") as f:
            f.write(f"version={v_app}\netiqueta=v{v_app}\ninstalador=OrganizadorPrincess_Setup_{v_app}.exe\n")


if __name__ == "__main__":
    main()
