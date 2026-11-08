"""
utils/sonido.py
Reproducción de tonos de aviso (Windows winsound).
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.
"""
import threading

def _reproducir_sonido_aviso(tipo: str = "aviso"):
    """Reproduce un tono de sistema al mostrar un popup.
    tipo: 'aviso' | 'vacaciones' | 'festivo'
    """
    def _play():
        try:
            import winsound
            if tipo == "vacaciones":
                # Melodía suave: dos notas ascendentes
                winsound.Beep(880, 180)
                winsound.Beep(1100, 280)
            elif tipo == "festivo":
                # Tres notas festivas
                winsound.Beep(880, 150)
                winsound.Beep(1100, 150)
                winsound.Beep(1320, 300)
            else:
                # Aviso estándar: tono doble llamativo
                winsound.Beep(1000, 200)
                winsound.Beep(1000, 200)
        except Exception:
            # Fallback: pitido de sistema si winsound falla
            try:
                import winsound as _ws
                _ws.MessageBeep(_ws.MB_ICONEXCLAMATION)
            except Exception:
                pass  # UI — ignorar silenciosamente
    threading.Thread(target=_play, daemon=True).start()
