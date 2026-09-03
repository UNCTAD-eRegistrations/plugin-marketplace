# The spirit, session by session

What this file is: the evidence behind [the criteria](criteria-change-document.md). For each session, what Frank asked in his own words, what changed in the document, and what it means for the next one.
The measure: prose words with the drawn screens excluded, counted by `prose_measure.py`. Where no saved version exists the count is marked a proxy.

## 18-08-2026. "A realistic modification to the Lesotho renewal services for sole proprietors"

Ledger `2026-08-18-9bf00fbc.md`, from 14:28.

**What he asked.** The opening brief was long and exhaustive: two routes, seven flows, a field-by-field proposal, a bot-by-bot proposal, every GDB read and write, officer tasks, open policy questions, "for every statement about current behaviour, cite the BPA service, field, bot, GDB table or view that proves it", and a closing line that named the real aim: "We will use this task as a way to improve our method to conceive changes in e-regulation services."

Thirty nine minutes after the first delivery he refused it:
> "Your writing is too jargon-y for the director. It has to be much simpler. it must also be more concise. Eliminate words which are not needed." (15:07)
> "This document is totally confusing and useless... You should not overwhelm me with documents and words. This is too much." (15:10)
> "This document is not linked to the others... give me one document with an index and then we'll see from there." (15:25)
> "A good index should show what the title of this page is... so that I see what are the members of the index." (16:13)
> "Remove that A is selected, we have not decided yet." (16:54)

**What changed.** [proposal.md](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/proposal.md) was written in one pass at 4,469 words (proxy, the ledger's own count), beside a mockup, a migration brief, a service note and six proofs. Eleven documents by 15:25. The session archived the how-we-conceived-it page, built one index, and wrote the choices-first rule into the method.

**The spirit.** The brief asked for everything; what he wanted was one door. Exhaustiveness is the analysis, not the document. A page that narrates how the work was done is noise. Nothing is shown as decided before he decides it.

## 20-08 to 23-08-2026. The change document itself, then the cookbook cut

Ledger `2026-08-20-3695a483.md`, 40 messages, 242 edits to `change.html`.

**What he asked.** First the screens, drawn from the live service and wrong on the first pass:
> "The screen doesn't look like this image 1 check well. There's no button called Register sole proprietorship and this button is called register business and it is above, not there." (21-08, 06:35)
> "Still wrong, the register business button is within the top line in the block. Check well in the BPM and reproduce here." (06:56)
> "what are these gray lines you put in the screens here they do not appear in the bpa check... modify here and modify in the rules and in the knowledge files" (07:53)
> "In this and in all other proposed screens you put one field per line. This is not our practice. We usually create at least two and generally three and four columns." (07:57)

Then the change itself, and what a recovery is:
> "it should not be only renew a business ID or license because maybe you just want to recover your business ID or license... why do you propose if you want to renew a business or a license? You should know that because we have clicked either on find my sole property shape or find my license." (07:26)
> "We should show here all the information we have for record in the business ID GDB. And we should offer the possibility to complete what is missing." (08:14)

Then the list of what the change touches:
> "In the change triggers, we just see the bots, but we need to mention everything that could be triggered. Bots, certificates, what else? ... Even though there's no change, we should mention no change in certificate, no change in what else." (10:00)
> "Do we need all this text? ... try to make this part more concise. Then what you put in the column bot is confusing. Is it the name of the bot or is it what it does?" (10:00)
> "I don't understand what leave alone means... put a collapsible section called something like changes at a glance... I think that this text is not necessary. It doesn't add anything. It just adds noise." (10:10)

**What changed.** `change.html` was born and grown here to 8,952 prose words, 11,100 words with the screens (measured on the 23-08-2026 file, byte-identical to the version that stood on 01-09). [proposal.html](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/proposal.html), 4,270 prose words, stopped being the document.

**The spirit.** The screen is the contract, so the drawing must be the live screen, in the house layout, or the document lies. Name every category the change touches, including the ones that do not change. A column carries a name, not a description. Text that explains how to read the page is noise.

## 23-08-2026. "It must look and feel like a cookbook"

Ledger `2026-08-23-70c91254.md`, 18 messages.

**What he asked.**
> "It is a method to make a change in an e-reiteration service. We need to improve it in the sense that it must look and feel like a cookbook. It means that all words have to be very concrete, very easy to understand. We should put less information on each page and remove all words which are not necessary." (08:03)
> "Julien, as all human beings, is somebody who cannot manage as much information as you can, so in each page there should be only the information we can put in our mental buffer. That's why I requested that the index be only three cards." (08:03)
> "we need to impose, in all future sessions, the spirit of removing unnecessary words, avoiding unnecessary comments, and saying things directly. This is not the case for the time being. We need to find where to impose this role deeply." (08:09)
> "we need to give a proper title to thhis page, so that Julien knows what it is... put this as small title (first part), maybe in capital letters and b lue and black normal fonts below for title" (09:02)
> "this is not orange, i want a plain orange like traffic lights" (09:18)
> "Je ne comprends pas ce que tu dis pour le D, créons une adresse sans le D." (07:54)

**What changed.** The index page fell from 255 prose words in 21 blocks ([the archived version](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/zarchive/index-avant-simplification-22-08-2026.html)) to 22 prose words in 2 blocks ([index.html](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/index.html)), three cards, three doors. The document moved to a plain address, `smartrules.ai/service-change-doc`.

**The spirit.** One page holds what one head holds, and he counts the doors. The rule is not a preference to remember, it is something to impose in the machine.

## 27-08 and 28-08-2026. The colleague, and the plumbing he must never see

Ledger `2026-08-18-9bf00fbc.md` again, from 15:32 on 27-08.

**What he asked.**
> "There's a part of the document which is the agreed part, and there's a part of the document which is his proposals." (15:47)
> "i dont understand this, all should happen withing claude and the change documebnt, why do you give J teh address of the repo, why does it need it? all should be automated, why should it clone it himself, this sjhould be part of the skill, what is this pull request? J should not know about this, thi sis technical cooking," (17:27)
> "the idea was that Julien can use the change document to propose changes, in his own tabs in the various sections, and that can look at thos poprosals and accept them or not." (17:52)

**What changed.** The pages moved into [the shared repository](/Users/unctad/Claude/3%20-%20Projects/service-change-documents), and the second address and the preview copy built that day were refused and removed. The document itself did not change: the file committed on 27-08-2026 is byte-identical to the 23-08 one.

**The spirit.** A colleague says what he wants changed and gets the document back. Anything he has to install, clone or merge has already failed. And the core tool was frozen for nine days while its collaboration layer was built, which is what he settled on 02-09-2026: "Julien is an anecdotal aspect of the tool".

## 01-09-2026. An outside restyle, and the first UI verdict

Ledger `2026-09-01-ea07fb1a.md`, 2 messages.

**What he asked.**
> "See this UI proposal and check the Eric Kennedy UI rules and tell me if it complies with the rules." (16:53, with a file he had downloaded himself)
> "make new proposal based on change 1 and integrating the kennedy rules" (17:20)

**What changed.** [The check](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/review-kennedy-01-09-2026.html) measured the restyle: 11 rules met, 7 broken, 3 blocks deleted. Broken by arithmetic, all measured on the served page: lines of 86 characters against a ceiling of 75, body at 16 px against a floor of 18 on a reading document, 7 text sizes where the method asks about 4, and a band 323 px wide left empty down the length of a page 16,000 px tall. [change-2.html](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/renew-not-on-dashboard/change-2.html), the repaired restyle, measures 8,715 prose words against 8,952: a restyle, not a rewrite.

**The spirit.** He went outside the house for the look, and outside the house for the rules to judge it. The presentation was never his to fix; it was ours, and it had not moved since 23-08.

## 01 and 02-09-2026. The line-by-line pass

Ledger `2026-08-18-9bf00fbc.md`, from 14:37 on 01-09. Fifty four saved changes, measured and drawn out in [Section 7 of the criteria](criteria-change-document.md#7-lessons-measured-on-the-session-of-01-and-02-09-2026): 8,952 prose words to 6,432, 51 blocks removed, the navigation rebuilt as a left rail.

## Sessions that only passed nearby

- `2026-08-18-928d25da.md`, `2026-08-26-71625077.md`, `2026-08-26-84239e71.md`, `2026-08-27-27208469.md`, `2026-08-27-5cef1022.md`, `2026-08-27-6321100d.md`, `2026-09-01-c31af879.md`: the studio, the free zones needs assessment, Valentina, the speakers, the marketplace. No edit to the change document. Two lines carry over: the free zones session born the `changes-on-top` skill, a lettered redline on a document with the verdict recorded in place, which is the same idea as the colleague's tab; and Frank's standing complaint there, "for some reason your propsal is less readable that the former UI, do you know why? it looks more bulky" (27-08-2026, 00:45).
- `2026-08-20-788ef947.md`: the vocabulary checker driven to zero on another change document.
- `2026-08-29-3d405956.md` and `2026-08-29-90e87bad.md`: the space registry. One line belongs here, said while looking at a registry page: "How can we transcend the rules of this, what you call the house rules? Can we make a very nice business registry site? How would you do that?" (30-08-2026, 19:06).
- `2026-09-02-31c36576.md` and `2026-09-02-fd15e7d6.md`: the request that produced this file.

## The spirit across all sessions

1. **One document, one index, one address.** Every part of a change lives inside one addressable page whose index names its own members. 18-08, 23-08, 27-08.
2. **The screen is the argument.** Under a drawing, one line. A bold lead with a paragraph under it is commentary, and commentary is the waste. 20-08, 01-09, 02-09.
3. **Draw what renders, where it renders.** The live screen, the real button in its real place, three columns to a row, no furniture the interface does not have. 21-08.
4. **Name every category the change touches, including the ones that do not change.** Bots, certificates, screens, words, the GDB tables. 21-08.
5. **Cases are numbered, bulleted and named.** Case 1, Case 2, one bullet each, counts in digits. 01-09.
6. **Everything on the page has an audience and a real name.** Text for the applicant, for the officer, or for the record; a panel named only if that is its name; invented labels and unexplained pills are defects. 01-09, 02-09.
7. **Restructure when you learn, do not patch.** A rule understood mid-session moves whole sections, and what was learned goes into the country knowledge file. 21-08, 01-09.
8. **The page keeps the reader's place.** One navigation, in one column, the open section ticked, one control folding a whole group, and the view surviving a reload. 02-09.
9. **Count the doors: a page holds what one head holds.** The index is three cards; 255 prose words became 22 the day he counted them. 23-08.
10. **Impose the spirit in the machine, not in a reminder.** "We need to find where to impose this role deeply." 23-08, and the three checkers driven to zero since 22-08.

## The UI spirit of the last sessions, and where the house rules fight it

**What he started asking for.** On 01-09 and 02-09-2026 the requests stopped being about words and became about the page as an instrument: everything collapsible but readable at a glance; a left column menu that collapses sideways, with an icon per element that evokes its section when narrow; one open section, the rest closed, the open one ticked; the section links in the rail only and never repeated on the right; one control per section that folds all its subsections; the choice remembered between visits; the markers, legends and pills gone. His own verdict on the pace of it: "fix, pay attention, we have been on this for a long time now, setting up a vertical index is a routine task" (02-09, 12:04). Alongside, on 01-09 he brought a restyle of our page that he had downloaded, and asked for it to be judged against an outside method.

**Where the house rules strain against that.** No resolution here, these are Frank's to settle.

- **A small bold title on every block.** [~/.claude/CLAUDE.md](/Users/unctad/.claude/CLAUDE.md) §Communication, repeated in [the format skill](/Users/unctad/.claude/skills/er-implementation-plan/SKILL.md) as "Every block carries a small bold title". Evidence against: of the 51 blocks removed on 01 and 02-09, 3,889 words, nearly all were a bold lead with a paragraph under a screen. The rule that shapes a reply manufactures the waste in a document whose content is drawings.
- **The glance document, rule 27.** [feedback_html_output_rules.md](/Users/unctad/.claude/projects/-Users-unctad-Claude/memory/feedback_html_output_rules.md): "every paragraph opens with a bold lead, and the bolds alone chain into the summary", plus "slim top bar with section links". Evidence against: 02-09, "we shliuld see the tabs only in the left column, remove from the right column". The top bar of jump links was replaced by the rail he asked for.
- **Collapsible, open by default.** Same file, rule 7: sections start open and the open or close-all switch is "optional now, and pointless on a page whose sections all start open". Evidence against: "Put it at the top, but close by default. Visible, but close by default." (21-08); "indicates which tab is open by default, all others are closed" (02-09); "for each section with subsections, show next to the section name an icon to open/close all subsections" (02-09). The format skill says the opposite of the memory rule: all sections collapsed by default. Two house rules disagree, and the document follows neither cleanly.
- **The reading width.** Rule 5 says 65ch, with an exception making working documents run full width; rule 14-bis says prose at most 65ch; the Kennedy method the same page invokes says 50 to 75 characters, which measured out at 58ch. Evidence: the same page is asked for three widths, and the measured result is a band 323 px wide left empty down 16,000 px of page.
- **The type scale.** Rule 14-bis fixes five steps with the body at 1rem. Kennedy asks 18 to 24 px on a document that reads like a book, and about four sizes. Measured on the restyle Frank brought: body 16 px, 7 sizes.
- **The token checker on every HTML written.** [check-tokens.py](/Users/unctad/Claude/9%20-%20System/ui-ux/check-tokens.py) runs as a hook on every page written and refuses a raw colour outside `:root`. Measured on the current change document: 142 refusals, almost all inside the drawn BPA screens, which exist to quote the real interface. Screen truth and token discipline pull in opposite directions on this one page.
- **The head of the document.** The format skill prescribes a navigation bar, a title, a qualifier line, a provenance box and a row of index chips before the first section. Evidence against: the opening paragraph and the head box were removed on 02-09, and the chips went with the rail. The skill still prescribes the removed furniture.
- **The presentation choice was never offered.** The [modern-ui](/Users/unctad/.claude/skills/modern-ui/SKILL.md) skill is supposed to trigger on every new document and offer a choice of real models. It never ran on this document in fourteen days; on 01-09 Frank brought his own restyle from his Downloads folder instead.
