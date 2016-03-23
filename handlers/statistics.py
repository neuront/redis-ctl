import base
from models.polling_stat import PollingStat


@base.get('/stats/pollings')
def pollings(request):
    return request.render('pollings.html', pollings=PollingStat.query.order_by(
        PollingStat.id.desc()).limit(120))
