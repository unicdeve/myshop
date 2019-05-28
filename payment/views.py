from django.shortcuts import render, get_object_or_404, redirect
from orders.models import Order
import braintree

from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
import weasyprint
from io import BytesIO


def payment_process(request):
  order_id = request.session.get('order_id')
  order = get_object_or_404(Order, id=order_id)

  if request.method == 'POST':
    nonce = request.POST.get('payment_method_nonce', None)
    result = braintree.Transaction.sale({
      'amount': '{:.2f}'.format(order.get_total_cost()),
      'payment_method_nonce': nonce,
      'options': {
        'submit_for_settlement': True
      }
    })
    if result.is_success:
      order.paid = True
      order.braintree_id = result.transaction.id
      order.save()
      # create invoice e-mail
      subject = f"My Shop - Invoice no. {order.braintree_id}"
      message = f"Please, find the attached invoice for your recent purchase of item with order no. {order.braintree_id}"
      email = EmailMessage(subject, message, 'uniqueomokenny@gmail.com', [order.email])
      # generate PDF
      html = render_to_string('orders/order/pdf.html', {'order': order})
      out = BytesIO()
      stylesheets = [weasyprint.CSS(settings.STATIC_ROOT + 'css/pdf.css')]
      weasyprint.HTML(string=html).write_pdf(out, stylesheets=stylesheets)
      # attach the PDF file
      email.attach(f'order_{order.braintree_id}', out.getvalue(), 'application/pdf')
      email.send()
      return redirect('payment:done')
    else:
      return redirect('payment:canceled')
  else:
    client_token = braintree.ClientToken.generate()
    print(f'{order} : {order_id}')
    return render(request, 'payment/process.html', {'order': order, 'client_token': client_token})



def payment_done(request):
  return render(request, 'payment/done.html')


def payment_canceled(request):
  return render(request, 'payment/canceled.html')
