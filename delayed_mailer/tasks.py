from celery.decorators import task

@task
def delayed_send(obj):
    obj.send()
