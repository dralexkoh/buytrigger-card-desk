"""Shared weekly digest band used by stories, news and price pages."""
from html import escape

def digest_signup_html(form_id, campaign=None):
 # campaign is accepted so existing callers stay valid. Every page uses one band.
 del campaign
 safe=escape(str(form_id), quote=True)
 title_id='digest-title-'+safe
 input_id='digest-email-'+safe
 return (
  '<section class="digest-signup digest-signup-article" id="digest-signup-'+safe+'" aria-labelledby="'+title_id+'">'
  '<div class="digest-band">'
  '<div class="digest-copy">'
  '<span class="kicker red-text">FREE WEEKLY DIGEST</span>'
  '<h2 id="'+title_id+'">The week’s cards, in one email.</h2>'
  '<p class="digest-sub">Verified news, prices and Features, once a week.</p>'
  '</div>'
  '<form class="digest-form" action="https://buytriggercards.substack.com/subscribe" method="get" target="_blank">'
  '<input type="hidden" name="utm_source" value="site">'
  '<input type="hidden" name="utm_medium" value="signup">'
  '<input type="hidden" name="utm_campaign" value="digest-band">'
  '<label for="'+input_id+'">Email address</label>'
  '<div class="digest-controls">'
  '<input id="'+input_id+'" name="email" type="email" required autocomplete="email" placeholder="you@example.com">'
  '<button type="submit">Subscribe</button>'
  '</div></form></div>'
  '<p class="digest-note">Free, weekly, unsubscribe anytime. Handled by Substack. <a href="index.html#privacy">Privacy note</a>.</p>'
  '</section>'
 )
