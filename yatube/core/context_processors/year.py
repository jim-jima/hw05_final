def year(request):
    """Добавляет переменную с текущим годом."""
    import datetime as dt
    return {
        'year': int(dt.datetime.now().strftime('%Y'))
    }
