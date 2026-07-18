# UAE Financial Services Regulatory Tracker - Source Configuration
#
# Each source defines:
#   name:          Display name
#   jurisdiction:  ADGM | DIFC | ONSHORE
#   regulator:     Short code shown in the digest
#   url:           Listing page to poll
#   link_patterns: Substrings a harvested link must contain to be treated as a
#                  regulatory item (keeps navigation/footer links out)
#   exclude_patterns: (optional) substrings that disqualify a link
#
# The scraper is deliberately generic (harvests <a> tags matching patterns)
# so it survives cosmetic site redesigns. Verify patterns still match if a
# source goes quiet for several weeks.

sources:
  # ---------------- DIFC ----------------
  - name: DFSA News
    jurisdiction: DIFC
    regulator: DFSA
    url: https://www.dfsa.ae/news
    link_patterns: ["/news/"]

  - name: DFSA Media Releases
    jurisdiction: DIFC
    regulator: DFSA
    url: https://www.dfsa.ae/media-releases
    link_patterns: ["/media-release", "/news/"]

  - name: DFSA Consultations
    jurisdiction: DIFC
    regulator: DFSA
    url: https://www.dfsa.ae/rulebook/consultation-papers
    link_patterns: ["consultation"]

  - name: DIFC Authority News
    jurisdiction: DIFC
    regulator: DIFC Authority
    url: https://www.difc.com/whats-on/news
    link_patterns: ["/whats-on/news/"]

  # ---------------- ADGM ----------------
  - name: ADGM Announcements (incl. FSRA)
    jurisdiction: ADGM
    regulator: ADGM / FSRA
    url: https://www.adgm.com/media/announcements
    link_patterns: ["/media/announcements/"]

  - name: ADGM FSRA Consultations
    jurisdiction: ADGM
    regulator: FSRA
    url: https://www.adgm.com/doing-business/consultation-and-guidance-papers
    link_patterns: ["consultation"]

  # ---------------- ONSHORE UAE ----------------
  - name: CBUAE News & Insights
    jurisdiction: ONSHORE
    regulator: CBUAE
    url: https://www.centralbank.ae/en/news-and-publications/news-and-insights/
    link_patterns: ["/news"]

  - name: CBUAE Rulebook Updates
    jurisdiction: ONSHORE
    regulator: CBUAE
    url: https://rulebook.centralbank.ae/en/view-revision-updates
    link_patterns: ["/rulebook/"]

  - name: SCA News
    jurisdiction: ONSHORE
    regulator: SCA
    url: https://www.sca.gov.ae/en/media-center/news.aspx
    link_patterns: ["/media-center/", "/news"]

  - name: VARA Announcements (Dubai onshore VAs)
    jurisdiction: ONSHORE
    regulator: VARA
    url: https://www.vara.ae/en/media/
    link_patterns: ["/media/", "/announcement", "/news"]

# Keyword relevance filter (used when no ANTHROPIC_API_KEY is set, and as a
# pre-filter before AI classification). An item is kept if its title matches
# any keyword OR it comes from a consultations/rulebook source.
keywords:
  - regulation
  - rulebook
  - rule
  - consultation
  - guidance
  - circular
  - decree
  - law
  - amendment
  - framework
  - enforcement
  - fine
  - censure
  - licence
  - license
  - aml
  - sanctions
  - prudential
  - crypto
  - virtual asset
  - token
  - stablecoin
  - fund
  - insurance
  - banking
  - payment
  - market
  - disclosure
  - listing
  - conduct
  - supervision
  - dear sirs
  - notice
