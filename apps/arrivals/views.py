# -*- encoding: utf-8 -*-

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.lan.models import Attendee, LAN, Ticket, TicketType
from apps.seating.models import Seat


@permission_required('lan.register_arrivals')
def home(request):
    lans = LAN.objects.filter(end_date__gte=datetime.now())
    if lans.count() == 1:
        return redirect('arrivals', lan_id=lans[0].id)
    else:
        lans = LAN.objects.all()

    return render(request, 'arrivals/home.html', {'lans': lans})


@ensure_csrf_cookie
@permission_required('lan.register_arrivals')
def arrivals(request, lan_id):
    lan = get_object_or_404(LAN, pk=lan_id)
    attendees = Attendee.objects.filter(lan=lan)

    breadcrumbs = (
        (lan, reverse('lan_details', kwargs={'lan_id': lan.id})),
        (_(u'Arrivals'), ''),
    )

    ticket_types = TicketType.objects.filter(lan=lan)
    tickets = Ticket.objects.filter(ticket_type__in=ticket_types)
    user_seats = {}
    ticket_users = {}

    for ticket in tickets:
        ticket_users[ticket.user] = ticket

    paid_count = 0
    arrived_count = 0
    for attendee in attendees:
        if Seat.objects.filter(user=attendee.user, seating__lan=lan):
            user_seats[attendee] = Seat.objects.get(user=attendee.user, seating__lan=lan)
        if attendee.has_paid:
            paid_count += 1
        if attendee.arrived:
            arrived_count += 1

    paid_count += len(tickets)

    return render(request, 'arrivals/arrivals.html',
                  {'attendees': attendees, 'lan': lan,
                   'paid_count': paid_count, 'arrived_count': arrived_count, 'breadcrumbs': breadcrumbs,
                   'tickets': tickets, 'ticket_users': ticket_users, 'user_seats': user_seats})


@permission_required('lan.register_arrivals')
def toggle(request, lan_id):
    if request.method == 'POST':
        username = request.POST.get('username')
        toggle_type = request.POST.get('type')
        previous_value = request.POST.get('prev')

        lan = get_object_or_404(LAN, pk=lan_id)
        user = get_object_or_404(User, username=username)
        try:
            attendee = Attendee.objects.get(lan=lan, user=user)

            if int(toggle_type) == 0:
                attendee.has_paid = flip_string_bool(previous_value)
            elif int(toggle_type) == 1:
                attendee.arrived = flip_string_bool(previous_value)
            else:
                raise Http404

            attendee.save()

        except Attendee.DoesNotExist:
            messages.error(request, _(u'{user} was not found in attendees for {lan}.').format(user=user, lan=lan))

        return HttpResponse(status=200)
    return HttpResponse(status=404)


def flip_string_bool(val):
    if val == 'True':
        return False
    elif val == 'False':
        return True
