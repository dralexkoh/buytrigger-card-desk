"""Shared Substack weekly digest used by stories, news and price pages."""
def digest_signup_html(form_id, campaign=None):
 title_id='digest-title-'+form_id
 subscribe='https://buytriggercards.substack.com/subscribe?utm_source=site&amp;utm_medium=signup'
 if campaign:
  if any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in campaign):
   raise ValueError('Unusable digest campaign')
  subscribe += '&amp;utm_campaign='+campaign
 return (
  '<section class="digest-signup digest-signup-article" aria-labelledby="'+title_id+'">'
  '<span class="kicker red-text">FREE WEEKLY DIGEST</span>'
  '<h2 id="'+title_id+'">The week’s cards, in one email<span class="red-text">.</span></h2>'
  '<p>Verified news, prices and Features, once a week. Free, and easy to leave.</p>'
  '<div class="digest-embed"><iframe src="https://buytriggercards.substack.com/embed" title="Subscribe to BuyTrigger.Cards Weekly" loading="lazy" width="480" height="320" frameborder="0" scrolling="no"></iframe></div>'
  '<p class="digest-consent">By signing up you agree to receive the weekly BuyTrigger.Cards digest by email. You can unsubscribe at any time.</p>'
  '<p class="digest-privacy">Substack sends the confirmation email and applies its <a href="https://substack.com/privacy" target="_blank" rel="noopener noreferrer">privacy policy</a>. We never see your password. See our <a href="index.html#privacy">privacy note</a>.</p>'
  '<p class="digest-fallback">If the form doesn’t appear, <a href="'+subscribe+'" target="_blank" rel="noopener noreferrer">subscribe on Substack</a>.</p>'
  '</section>'
 )
