# Criteria, the change document tool

What this file is: the tool's aim and Frank's distilled judgments, 18-08-2026 to 02-09-2026, in his own words where they exist.
How sessions use it: read before writing or reviewing a change document; when Frank corrects or approves, add a numbered criterion with the why.

## 1. What the tool is for

Frank's own framing, written 02-09-2026:

1. eRegistrations is a visual no-code metalanguage used by UNCTAD and other service designers to develop online services.
2. The change document is a tool for service designers to define and implement, with AI, changes in an existing eR service.
3. Analyzing a complex change implying numerous changes in various parts of the system demands a lot of attention and mental energy from the service designer. The tool assists in this exercise: the service designer defines the requested change in simple language, the tool analyses all changes required on the basis of the current situation and presents both in a very simple and clear way. All is visual, with as little text as possible since there is a lot of info, and only the necessary and sufficient info should be shown, not to overwhelm the service designer.
4. The tool also presents the implementation plan in the simplest possible way, with ways for the human to follow easily.
5. UX and UI are key since there is a lot of info and it must be as clear as possible.
6. The tool speaks the eR language (Rosetta Stone, glossary, terms list) so the service designer understands what it says.
7. The collaboration layer is a separate matter, see [Section 5](#5-set-aside-for-now).

In his own words, across the sessions, what the tool must do and must never do:

> "It is a method to make a change in an e-reiteration service. We need to improve it in the sense that it must look and feel like a cookbook. It means that all words have to be very concrete, very easy to understand. We should put less information on each page and remove all words which are not necessary." (23-08-2026)

> "Julien, as all human beings, is somebody who cannot manage as much information as you can, so in each page there should be only the information we can put in our mental buffer." (23-08-2026)

> "You should not overwhelm me with documents and words. This is too much. You should be more concise." (18-08-2026)

> "Your writing is too jargon-y for the director. It has to be much simpler. it must also be more concise. Eliminate words which are not needed." (18-08-2026)

> "We need to remove all unnecessary parts. You should not comment on things; we should say things." (23-08-2026)

> "This document is not linked to the others. It is key and this is primary for a methodology that you issue clear documents linked with each other with an index." (18-08-2026)

> "What's the point of all this? What is the value added of this part? First of all, I don't understand anything." (01-09-2026)

> "make all sections and subsections collapsible... I should be able to read it at a glance." (01-09-2026)

## 2. Who reads it, and what they must be able to do

The reader is a service designer: technical about eRegistrations, not a programmer, working from what the screens show. What they bring is the change in plain language, a sentence or two. What they must get back: the current situation as the live service renders it, every change the request requires, named and located, and a plan they can act on step by step.

"Not overwhelmed" is Frank's own measure, not a stylistic preference: "in each page there should be only the information we can put in our mental buffer" (23-08-2026). One page holds what one head holds; folding hides detail but the top of any page must still read at a glance ("I should be able to read it at a glance", 01-09-2026). A page that needs explaining has already failed: "What's the point of all this?... I don't understand anything." (01-09-2026).

The full editing spirit behind every sentence is [leaflet-editing-spirit.md](leaflet-editing-spirit.md): say the thing, never present the page or comment on it. This file does not repeat that rule, it extends it with what the August and September sessions settled specifically for the change document.

## 3. The criteria

The July style rules already govern writing the logic and not the configuration, his three categories (screens, bots, GDB), strict eR vocabulary, evidence-tagged claims, canvas-true drawings, collapsed sections with index chips, the phase and test grammar, and the announce-then-explain order. Full text: [feedback-er-implementation-plan-style.md](/Users/unctad/.claude/projects/-Users-unctad-Claude/memory/feedback-er-implementation-plan-style.md). What follows is what 18-08 to 02-09-2026 added or confirmed hard enough to freeze.

### What the document shows

**C1. One document, one index.** All the parts of a change (proposal, current state, end state, migration, phases) live inside one addressable document with one clear index; scattered separate files confuse the reader.
> "give me one document with an index and then we'll see from there" (18-08-2026).
Why: five unlinked files sent Frank in circles the same afternoon.

**C2. The index names its own members.** The index lists and links every real part of the page it opens, never a generic label standing in for them.
> "A good index should show what the title of this page is... this document referred to in the index so that I see what are the members of the index." (18-08-2026).

**C3. Title says the decision.** A page title names the actual question or content at stake, never a generic label.
> "This is not a good title find a better one" (18-08-2026).

**C4. No premature verdict.** A proposal not yet chosen is never shown as already selected.
> "Remove that A is selected, we have not decided yet." (18-08-2026).

**C5. Structure follows the real world.** Screens are grouped the way the world is organized, dashboard then business then its cases, licence then its cases, never by a category invented for the document.
> "If it is dashboard and then you put the four cases, or you put dashboard and then businesses and then case one, case two, and then licenses and activities, case one, case two" (01-09-2026).
Why: settled into the document's own section order (My Dashboard Businesses, My Dashboard Licenses and Activities, the new service recovering a business, the new service recovering a licence).

**C6. Cases are named Case 1, Case 2.** Whenever a screen splits on a condition, each side gets its own plain number.
> "you should say case one and case two. It will be clearer." (01-09-2026).

**C7. Change in short, four parts in order.** The opening always runs Why, then What we change, then How it works, then What it touches; the tension lives inside "today", never as a part of its own (already in the style rules). Confirmed 02-09-2026 with the case bullets and digits added below.

**C8. Bullets for the cases.** Wherever the change splits into cases, each is its own bullet, never folded into a running sentence.
> "Put bullet points for the different cases. It will be easier." (01-09-2026).

**C9. Digits, not spelled numbers.** In the change-in-short section, counts are written as digits.
> "put numbers in neumbers not in letters" (01-09-2026).

### What it never shows

**C10. No GDB name to the applicant.** No drawing an applicant reads may name a GDB or a legacy store; that exists for the registry only.
> "we should not show applicants any mention of the e-licenses July 2026 table nor of any other table. This is just for us." (02-09-2026).
Confirmed: "No GDB store is named in anything an applicant reads" (02-09-2026 handover).

**C11. No unexplained sentence.** A sentence whose meaning is not obvious on first read is removed, not left for the reader to puzzle over.
> "remove last sentence, what does it mean?" (02-09-2026).

**C12. No noise.** An image, block or line that adds nothing is removed outright, not softened.
> "this creates noise (image 1) and is not useful" (01-09-2026); "Remove all. Nothing is useful. And do the same in all cards." (01-09-2026).

**C13. No unjustified section.** A section earns its place by what it changes in the reader's understanding; if it cannot say what it is for, it is cut.
> "What's the point of all this? What is the value added of this part? First of all, I don't understand anything." (01-09-2026).

**C14. No invented screen name.** A block or panel is named only if that is its real name on the live screen; an invented label is a defect.
> "We have nothing called business panel. What does it mean? Is it something you invented? This is screen, so clarify this." (01-09-2026).
Why: extends the style rules' screen-truth rule from fields to named regions.

**C15. AI instructions never sit in human text.** A build note meant for the AI implementer goes in its own marked technical block, never mixed into the sentences a human reads.
> "If it is a bill instruction for AI, put it in an AI-only section, not for a human reader." (01-09-2026).
Confirmed: "no build instruction in the human part" (kit 1.2.0, 02-09-2026).

**C16. No unmarked audience.** Every piece of text on a drawing is clearly for the applicant, the officer, or the record itself; text of unclear audience is removed.
> "what did you put this text? is it for us or for tghe applicant? i would remove." (02-09-2026).

### How it is drawn

**C17. A legend entry earns its place on that screen.** The legend under a drawing lists only marks that appear on it, never a universal key repeated everywhere. Confirmed, kit 1.2.0, 02-09-2026.

**C18. One line per screen.** A caption under a drawing is one line, not a paragraph. Confirmed, kit 1.2.0, 02-09-2026.

**C19. One clear reference per number.** Any number or reference named in text says plainly what it is.
> "which number are ou talking about? the nbr on the certif? if not it is worth explaining" (01-09-2026).

**C20. Two numbers never share one word.** When two distinct figures are at stake, they get two words, not one vague word standing for both. Confirmed, kit 1.2.0, 02-09-2026.

**C21. Sibling inconsistency is explained, not silent.** If one card in a set carries a mark that its sibling lacks, the difference is stated.
> "you see that there's a determinant in the first image and not on the second one. Justify why." (01-09-2026).

**C22. Every effect and action drawn on a screen is explained.** A visual device with no obvious meaning is removed or given a plain-word key.
> "what do these pills mean?" (01-09-2026).

**C23. The navigation lives in one place.** Once section links have a home, the left rail, they are not duplicated in a second spot on the same page.
> "we shliuld see the tabs only in the left column, remove from the right column, we should see there only the open tab" (02-09-2026).

**C24. The current location is marked.** The open section and the chosen view carry a visible check, not just a colour change.
> "the selected tab shluld be ticked" (02-09-2026).

**C25. Reader's place is remembered.** Which sections are open and which tab is chosen survives a reload; it does not reset itself.
> "my selection should be kept, for the time being it is refreshed with every refresh" (02-09-2026).
Confirmed: "remembered in the browser between visits" (02-09-2026 handover).

**C26. A folded rail still speaks.** When the navigation narrows to icons only, each icon still evokes its section, never a blank strip.
> "when closed i should see icons which evoque each element" (02-09-2026).

**C27. One control folds a whole group.** A section holding subsections carries one icon that opens or closes all of them together.
> "for each section with subsections, show next to the section name an icon to open/close all subsections" (02-09-2026).

**C28. Fold everywhere, glance at the top.** Every section and subsection collapses, and the reader still takes the shape of the whole page in one look.
> "make all sections and subsections collapsible... I should be able to read it at a glance." (01-09-2026).

**C29. A vertical index is routine, not research.** Building the section navigation is a settled pattern to apply, not a problem to re-solve each time.
> "setting up a vertical index is a routine task" (02-09-2026).

### The words

**C30. The page's own identity: kicker, then name.** The page opens with a small blue capitals line naming the collaboration and its scope, the service name in plain black below it, smaller than the page title.
> "put this as small title (first part), maybe in capital letters and b lue and black normal fonts below for title" (23-08-2026).

**C31. An action card stands out in a plain colour.** A card whose nature differs from its siblings, something to install or act on, is marked in a flat, saturated colour, never a muted tone.
> "this is not orange, i want a plain orange like traffic lights" (23-08-2026).

**C32. Purpose before content.** A request is read as it usually arrives: why before what.
> "put why first, and adapt the second sentence" (01-09-2026).

### The plan and the phases

**C33. Phase cards, tests at the end, the final test as the closing section.** Already fully in the style rules; the August and September sessions add nothing new here. This change's own phases and final test remain unreviewed by Frank, see [Section 6](#6-settled-on-the-lesotho-change-itself).

### The method: read the live service, screens are the contract, from the current situation

**C34. The built service must match the document.** What ships is checked against the approved screens; a mismatch is fixed, not explained away.
> "Remove and the built service must match them." (01-09-2026).

**C35. A live read has an expiry, not just a stamp.** A screen's read date is not a permanent label; a stale read is refreshed before the document ships, not just relabeled.
> "read 21 August is too old, we should read again" (01-09-2026).

**C36. Capture what you learn.** New understanding of the live service, which activities require a licence, how the legacy stores relate, is written into the country knowledge file, not just used once and dropped.
> "Read if this is mentioned in Lesotho MD. If it is not the case, record this information there there." (01-09-2026).
Why: two new parts were added to Lesotho.md the same day (Activities and licences; the Legacy group).

**C37. New understanding restructures, not patches.** When something learned mid-session changes the design, the document's structure is redone to fit it, not bent around the old one.
> "take into account what you discovered now, that some activities which are missing and for which a license is requested must be dealt with specially... you need to remove all what relates to activities in this business part." (01-09-2026).

**C38. Check the live screen before drawing it.** Already in the style rules (screen-truth: draw what renders, never the definition); confirmed again in this change: a drawing said a button sat in one place and it did not.
> "Still wrong, the register business button is within the top line in the block. Check well in the BPM and reproduce here." (21-08-2026).

## 4. What Frank refused

- **Colour on the invitation cards.** Tried, then removed. "Finally, let's remove the green from all these sections for license and sole proprietorship when you don't see any license or any sole proprietorship." (21-08-2026)
- **A muted orange.** Refused for a plain, saturated one. "this is not orange, i want a plain orange like traffic lights" (23-08-2026)
- **A second address, a preview copy of the document.** Built, then refused and removed, 27-08-2026: "there is no preview copy and no second address."
- **Separate Julien's remarks and Julien's proposals sections.** Tried, then folded into a try tab inside each section instead, 25-08-2026.
- **An opening paragraph, a box at the head.** Removed; the head now runs straight from the title into the sections, 02-09-2026.
- **Commentary paragraphs after "what changes".** Removed. "this long text after what changes is very confusing. Why should I read that? Either you remove it or just put what is important there" (01-09-2026)
- **AI build instructions inside human-facing prose.** Moved to their own marked block. "If it is a bill instruction for AI, put it in an AI-only section, not for a human reader." (01-09-2026)

## 5. Set aside for now

> "Julien is an anecdotal aspect of the tool, it is an attempt, maybe premature, to make the tool collaborative, let's concentrate on the core tool first." (Frank, 02-09-2026)

The collaboration layer, the try tabs per section, the shared repository, the remark tool, waits on this call. Its design record: the [25-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-25-aug-26.md) and the [27-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-shared-repository-27-aug-26.md).

## 6. Settled on the Lesotho change itself

- **Placement A.** The invitation sits where the missing record would have been listed, confirmed twice, 18-08 and 21-08-2026. [22-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-22-aug-26.md).
- **It recovers, it does not renew.** Named "Recover a Business ID or licence not shown on my dashboard", 21-08-2026. [21-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-21-aug-26.md).
- **No guide page.** The dashboard button carries the destination in a hidden field, 21-08-2026. [21-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-21-aug-26.md).
- **Two identity cases, the number decides.** A matching name changes nothing, 21-08-2026. [21-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-21-aug-26.md).
- **The wording of the invitations.** "Find my business", "Find my licence", "Find it" for the quiet links, 21-08-2026. [22-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-22-aug-26.md).
- **Read from Legacy, not DRF.** 21-08-2026. [21-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-21-aug-26.md).
- **Business ID mandatory in the licence path, ownership decided once.** 02-09-2026. [02-09-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-the-document-worked-with-julien-02-sep-26.md).
- **Companies parked for another change session.** 21-08-2026. [21-08-2026 handover](/Users/unctad/Claude/5 - Handovers/lesotho-renew-change-document-21-aug-26.md).

## 7. Lessons measured on the session of 01 and 02-09-2026

Fifty four saved changes, made by Frank line by line. Measured on the document before the session and after it, prose only, drawn screens excluded:

| | Before 01-09 | After 02-09 |
|---|---|---|
| Prose words, screens excluded | 8,952 | 6,432 |
| All words, screens included, Julien panes excluded | 10,953 | 13,683 |
| Prose blocks removed or rewritten | 51 blocks, 3,889 words | |

**L1. The commentary under a screen is the waste.** Nearly every removed block was a paragraph under a drawn screen, opened by a bold lead: What the screen does (583 words), How this was read (499), What changes (322), What this drawing is (261), Why this screen exists (222), What we want (220), What the person sees, Why this is here, Why they exist, What it costs, What is drawn, What is not drawn, Where it stops. The screen speaks; one line under it at most (C18).

**L2. A bold lead with a paragraph under it is commentary.** The pattern that serves a reply serves no change document. The grammar Frank kept: the title, then the screen, then one line; cases as bullets (C8); digits (C9); provenance as a date and a version, never the story of the reading.

**L3. The weight is now the screens, not the prose.** Prose fell by 28 percent while the page grew by 25 percent: five licence screens were drawn. The next simplification is how screens are shown (how many at once, one section at a time, how two cases sit), not more sentence cutting.

**L4. Restructure when you learn.** Activities left the business path for the licence path the moment the licence rule was understood; sections were regrouped by where they live on screen (C5, C37).

**L5. Markers gave way to one navigation.** Legend rows, pills and the chip row went; a fixed left rail with a show-only-this button per section and a fold-all button per title took their place, and the page remembers the view (C23 to C28).

**L6. What is still heavy after the session.** Fifteen prose blocks over 60 words, 1,393 words: the three checks the screens cannot show, the tests inside the phases, Legal ground, the Legacy assessment. The For the AI part is heavy too, and it is not for the human (C15).

## 7-bis. More criteria, from the sessions of 18-08 to 27-08-2026

Read from the session ledgers on 02-09-2026. The evidence trail, session by session, is [spirit-by-session.md](spirit-by-session.md). These extend Section 3 and carry on its numbering.

**C39. Three columns to a row.** A drawn screen lays its fields the way the house lays them, two to four columns, never one field per line.
> "In this and in all other proposed screens you put one field per line. This is not our practice. We usually create at least two and generally three and four columns." (21-08-2026).

**C40. No furniture the screen does not have.** A drawing adds no rule, band or line that the live interface does not render.
> "what are these gray lines you put in the screens here they do not appear in the bpa check... modify here and modify in the rules and in the knowledge files" (21-08-2026).
Why: the drawing is the contract, so an invented mark becomes a build instruction.

**C41. Every category is named, including the ones that do not change.** What the change triggers lists screens, bots, certificates, words and GDB tables, and says "no change" where nothing changes.
> "In the change triggers, we just see the bots, but we need to mention everything that could be triggered. Bots, certificates, what else? ... Even though there's no change, we should mention no change in certificate, no change in what else." (21-08-2026).

**C42. A column carries the name, not the description.** In a list of elements, the name column holds the element's real name, built to the naming template; what it does belongs in the description.
> "what you put in the column bot is confusing. Is it the name of the bot or is it what it does?" (21-08-2026).

**C43. Show everything held, and offer to complete what is missing.** Where the change reads a record, the document shows every field held and the offer to complete the gaps.
> "We should show here all the information we have for record in the business ID GDB. And we should offer the possibility to complete what is missing." (21-08-2026).

**C44. Never ask what the applicant has already said.** A question the flow already answered is removed from the drawn screen.
> "why do you propose if you want to renew a business or a license? You should know that because we have clicked either on find my sole property shape or find my license." (21-08-2026).

**C45. Three doors, and he counts them.** The index carries three cards, no more, each a door with a title to the point.
> "in each page there should be only the information we can put in our mental buffer. That's why I requested that the index be only three cards." (23-08-2026).
Measured: the index page fell from 255 prose words in 21 blocks to 22 words in 2 the same day.

**C46. No text that teaches how to read the page.** A line explaining what a column means or how to read a section is removed, and the thing itself is made plain.
> "I don't understand what leave alone means... I think that this text is not necessary. It doesn't add anything. It just adds noise." (21-08-2026).

**C47. A plain address.** The document's address carries no machine letters.
> "Je ne comprends pas ce que tu dis pour le D, créons une adresse sans le D." (23-08-2026).

**C48. The spirit is imposed in the machine, not remembered.** A rule about words or noise is enforced by a checker or a hook, never by a reminder in a file.
> "we need to impose, in all future sessions, the spirit of removing unnecessary words, avoiding unnecessary comments, and saying things directly. This is not the case for the time being. We need to find where to impose this role deeply." (23-08-2026).

**C49. The colleague never sees the plumbing.** Whatever a colleague must install, clone or merge has already failed; he says what he wants changed and gets the document back. Held with the rest of the collaboration layer in [Section 5](#5-set-aside-for-now).
> "why do you give J teh address of the repo, why does it need it? all should be automated, why should it clone it himself... J should not know about this, thi sis technical cooking," (27-08-2026).

**C50. The rail is the tabs.** The rail names the sections; the workspace shows one section's content and never its title again; the shown one is ticked; the rail pane is white against the workspace.
> "The menu on the left is tabs, this is the only place where the titles appear. On the tab working space you just see this tab." (03-09-2026)
Why: asked several times since 02-09; the 02-09 build kept the title rows as fold handles, so the titles stayed. Applied 03-09-2026.

**C51. The end situation follows the object, then the person's path.** Business, then Licence and activities; under each, On My Dashboard, then In the new service; the officer desk once, because ownership is decided once, on the business; Behind the screens last. Every group and case closed on a first visit; afterwards the page keeps what the operator opened.
> "it would probably be more logical to structure through having business and then under business having my dashboard and new service and the same for licenses activities" (03-09-2026); "by default all sections closed at beginning, after leave open those open by operator" (03-09-2026)
Why: the reader follows one object end to end; it replaces the 01-09 grouping by place (dashboard first, then the service).

**C52. The logic listing is the builder's, not the reader's.** A hidden block, a list of every determinant, a "logic spelled out" grid: none of it sits in the human part. The screens carry their effects and actions; the listing lives under For the AI. A grid in the human part wraps its text inside its columns.
> "I don't understand what this section is for. If there's a hidden block, it should be shown in the other screens, not here... We don't need a listing of all determinants, and it's not responsive; the text is not in the blocks." (03-09-2026)
Why: Behind the screens was moved whole into For the AI the same day; the human part of End situation reads Business, Licence and activities, The officer desk.

**C53. Group headings in the rail in small capital letters.** In the left pane, a heading that groups items (Business, Licence and activities, The officer desk) is set in small capitals, muted; the items under it in normal case.
> "the change-b version is better in the left pane, because the titles are in capital letters. It's better than what we have for the time being, so we should adopt this in our style." (03-09-2026)

## 8. The spirit in ten lines

Drawn from every session of the document, 18-08 to 02-09-2026. Each line is a rule to apply while writing or drawing, with the sessions that show it.

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

Where the house rules pull against this, with the evidence and no resolution: the closing part of [spirit-by-session.md](spirit-by-session.md).
