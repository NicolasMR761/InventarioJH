# Runtime hook — fuerza importar reportlab al inicio del exe
try:
    import reportlab
    import reportlab.pdfgen
    import reportlab.pdfgen.canvas
    import reportlab.lib
    import reportlab.lib.pagesizes
    import reportlab.lib.units
    import reportlab.lib.colors
    import reportlab.lib.styles
    import reportlab.lib.enums
    import reportlab.lib.utils
    import reportlab.platypus
    import reportlab.graphics
except Exception:
    pass
