from django.core.urlresolvers import reverse
from django.template.context import Context, RequestContext
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django import forms
from fanfouapi.models import FFUser
from django.conf import settings

def route(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('dashboard'))
    else:
        site_url = 'http://%s' % settings.FF_HOST
        return render_to_response('route.html',
                                  RequestContext(request,
                                                 locals()))

def signout(request):
    logout(request)
    return HttpResponseRedirect(reverse('route'))

@login_required
def update_profile_image(request):
    ffuser = FFUser.objects.get_by_user(request.user)
    api = ffuser.get_api()


    class ProfileImageForm(forms.Form):
        image = forms.ImageField()
        def save(self):
            img = self.cleaned_data['image']
            content = img.read()
            filename = img.name
            if isinstance(filename, unicode):
                filename = filename.encode('utf-8')
            return api.update_profile_image(filename=filename,
                                     content = content,
                                     file_type=img.content_type)
    if request.method == 'POST':
        img = request.FILES.get('image')
        form = ProfileImageForm(request.POST,
                                request.FILES)
        if form.is_valid():
            print form.save()
            return HttpResponseRedirect(reverse('update_profile_image'))
        else:
            print form.errors

    else:
        form = ProfileImageForm()
    u = api.verify_credentials()
    myid = api.get_user().id
    a = api.user_timeline(myid)
    for status in a:
        api.destroy_status(status.id)
        print(status.created_at)
        print(status.text)
        print(status.id)
    return render_to_response('update_profile_image.html',
                              RequestContext(request, locals()))

@login_required
def dashboard(request):
    ffuser = FFUser.objects.get_by_user(request.user)
    api = ffuser.get_api()
    start_up(api)

    return render_to_response('dashboard.html',
                              RequestContext(request,
                                             locals()))


from time import sleep
import heapq
import requests

class ProcessedStatus(object):
    def __init__(self, text):
        self.text = text

    def __lt__(self, obj):
        return self.negative_prob > obj.negative_prob

class SentimentClassify(object):
    def __init__(self):
        r = requests.post('https://ai.baidu.com/aidemo', data = {})
        self.cookies = r.cookies

    def run(self, text):
        r = requests.post('https://ai.baidu.com/aidemo',
                          cookies = self.cookies,
                          data = {
                              'apiType': 'nlp',
                              't1': text,
                              'type': 'sentimentClassify',
                          })
        # self.cookies = r.cookies

        print(r.json())
        result = r.json()['data']['items'][0]
        if result['confidence'] < 0.5:
            return -1
        return result['negative_prob']

def start_up(api):
    """
    1 hour send message
    5 minutes refresh timeline
    15 seconds have a sentiment classify
    15 seconds fo back friends
    """
    print(api.enable_notifications().__dict__)
    raw_input()
    TICK = 15

    unprocessed_statuses = []
    processed_statuses = []

    last_public_status_id = None
    last_home_status_id = None

    #myid = api.get_user().id
    #a = api.user_timeline(myid)
    sc = SentimentClassify()

    count = -TICK
    while True:
        count += TICK

        pass

        if count % 5*60 == 0 and len(unprocessed_statuses) < 1000:
            statuses = api.public_timeline()
            for status in statuses:
                if status.id == last_home_status_id:
                    break
                if hasattr(status, 'in_reply_to_status_id') and status.in_reply_to_status_id \
                        or hasattr(status, 'repost_status_id') and status.repost_status_id:
                    continue
                if len(status.text) < 10:
                    continue
                unprocessed_statuses.append(status)
            last_home_status_id = statuses[0].id

        if len(processed_statuses) < 1000 and len(unprocessed_statuses) > 0:
            status = ProcessedStatus(unprocessed_statuses.pop(0).text)
            status.negative_prob = sc.run(status.text)
            heapq.heappush(processed_statuses, status)
            print(processed_statuses[0].text)
            print(processed_statuses[0].negative_prob)

        if count % 60*60 and processed_statuses[0].negative_prob > 0.8:
            # post status
            pass

        sleep(TICK)



