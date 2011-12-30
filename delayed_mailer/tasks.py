from celery.task import task

@task()
def delayed_send(hash):
    from delayed_mailer.log import Group
    Group(hash).send()
