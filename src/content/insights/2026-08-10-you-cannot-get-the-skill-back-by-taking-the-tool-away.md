---
title: "You Cannot Get the Skill Back by Taking the Tool Away"
date: 2026-08-10
summary: "The Australian Public Service is projected to decrease staffing levels significantly over the next decade, raising concerns about the impacts of automation on employee competence. New research indicates that previous skills may not be recoverable once reliance on automation exceeds a certain threshold, emphasising the importance of careful sequencing in tool adoption to maintain essential capabilities."
themes:
  - "AI in Government"
image: ../../assets/insights/you-cannot-get-the-skill-back-by-taking-the-tool-away.jpg
wordpress: "https://russellbuzby.com/2026/08/10/you-cannot-get-the-skill-back-by-taking-the-tool-away/"
---
The Australian Public Service is forecast to reach an average staffing level of 217,256 this financial year. The Parliamentary Budget Office’s medium-term budget outlook, published on 14 July, sets out what returning the budget to balance by 2034-35 would take out of that figure: roughly 41,000 positions over a decade, with average staffing falling to about 189,000 by 2030 and 176,000 after that (Region, 2026). Ministers responded immediately and flatly. There is no direction to cut public service jobs, the APS is broadly the right size, and no overall reduction is expected.

Both of those statements can be true. The PBO produces scenarios under stated assumptions and the government is not bound by them, so the honest description of the 41,000 is a projection about arithmetic rather than a plan about people. A projection of that size still shapes behaviour, and every agency executive in Canberra has now read this one. What the projection does not settle is how a reduction of any size would actually be delivered, and the default answer to that in 2026 is automation.

Research published on 23 July should change how that answer is assessed. A dynamical systems model of competence and tool reliance finds the two are bistable: above a critical threshold of tool availability, user competence collapses irreversibly toward dependence, and the outcome is determined by the user’s history of practice more than by current access (*Competitive and Complementary Tools*, 2026). The word doing the work in that sentence is irreversibly. Past the threshold, restricting the tool does not bring the competence back, because competence was built by practice and the practice has already stopped.

That finding has an uncomfortable implication for the standard mitigation. When leaders worry about deskilling, the reassurance offered is usually reversibility: we can always dial the tool back, run manual exercises, restore the old process if the capability erodes. The model says the reassurance is misplaced for anyone already past the threshold. It also says something more useful, which is that sequencing determines the outcome. An organisation that builds the skill first and introduces the tool second lands in a different equilibrium from one that introduces the tool to people who never developed the skill, even if both end up with identical tools and identical policies.

I have written about the front end of this problem twice, and this research revises one of those pieces. [The Augmentation Trap](https://russellbuzby.com/2026/07/02/the-augmentation-trap-when-ai-productivity-eats-the-expertise-it-depends-on/) argued that productivity gains are captured now while skill costs are paid later on a different balance sheet, and [Knowledge Debt](https://russellbuzby.com/2026/07/29/knowledge-debt-when-the-team-ships-code-it-cant-explain/) described teams shipping work they cannot explain. In [Months to Destroy, Years to Rebuild](https://russellbuzby.com/2026/07/27/months-to-destroy-years-to-rebuild/) I priced the rebuild of capability lost in restructures. The bistability result suggests part of that rebuild estimate is optimistic. Some of what gets lost does not come back on any timeline, and the parts that do come back require the practice to restart, which is precisely what a smaller workforce running on automated tooling will not do.

A companion paper published two days earlier offers something practical. The Protocol for Human Preservation in AI-Optimized Organizations quantifies four systemic risks that standard cost-benefit analysis ignores: tacit knowledge erosion, resilience reduction, regulatory exposure and socio-institutional capital loss. It sets those out as an auditable five-gate framework intended to justify human-in-the-loop mandates and prevent automation choices that look efficient in the short term while accumulating organisational debt (*When Not to Automate*, 2026). Whether the specific gates hold up in practice matters less than what the framework provides, which is a defensible artefact. An executive who wants to keep humans in a process currently has intuition and anecdote. A five-gate assessment gives them something to put in front of a Finance official looking for savings, and that changes the outcome of the meeting.

The workforce side compounds all of this in a way the efficiency case never models. Research surfaced in mid-July on employee resistance finds it appears as avoidance, workarounds or compliance theatre when threat perceptions outpace coping capacity, and that overemphasising AI risk in internal communications makes adoption worse (*Resisting the Machine*, 2026). Put that alongside The Mandarin’s reporting that public sector burnout is driven by work design and communication failures instead of individual resilience (The Mandarin, 2026a), and alongside its account of workforce growth, budget pressure and pay bargaining converging into a single set of demands on the same executives (The Mandarin, 2026b). An APS asked to absorb headcount pressure while adopting AI, in an internal communications environment that emphasises threat, is an APS heading for workarounds and exhaustion.

Compliance theatre matters here beyond its cost in morale, because it corrupts the measurement. An organisation that thinks it has adopted a tool, when what it actually has is staff quietly routing around the tool, will make its next capability decision on false information. It will conclude that the automation delivered its savings and will plan the next tranche accordingly. Meanwhile the practice that maintains competence has stopped anyway, since the workaround is not the old craft either.

Automation should take work it genuinely does better than people do. The argument here is about the order of operations and the records kept along the way. Decide which capabilities the organisation must be able to perform without the tool, and say so explicitly before procurement rather than after. Sequence adoption so that staff who will supervise a system have first done the work the system does. Measure practice as well as output, because an output metric cannot distinguish a competent operator from a dependent one until the day the tool is unavailable. Treat the retained workforce as the deliberate half of an automation business case, with its own resourcing, instead of the residue left when the savings are counted.

There is a version of the next decade where the APS gets smaller because governments choose that, and it is a legitimate choice for a government to make and defend at an election. There is another version where it gets smaller by accretion, one automation decision at a time, each individually sensible, with the capability cost discovered somewhere around 2032 during something that cannot wait.

The PBO gave Australia a number. The more useful contribution this month came from a dynamical systems paper nobody in Canberra has read, and it says that the sequence in which you do this decides whether it can be undone.

## References
Competitive and Complementary Tools (2026). arXiv:2607.18460. <https://arxiv.org/abs/2607.18460>

Region (2026, 14 July). PBO says Labor’s surplus requires 41,000 APS job cuts. <https://region.com.au/pbo-says-labors-surplus-requires-41000-aps-job-cuts/982234/>

Resisting the Machine: Explaining Employee AI Resistance Using PMT and TTAT (2026). AMCIS 2026. <https://aisel.aisnet.org/treos_amcis2026/188>

The Mandarin (2026a, 15 July). Burnout in the public sector is about how work is experienced. <https://themandarin.com.au/316358-burnout-in-the-public-sector-is-about-how-work-is-experienced>

The Mandarin (2026b, 16 July). Bargaining, budgets, and fat cats: A perfect storm is on the way. <https://themandarin.com.au/316352-bargaining-budgets-and-fat-cats-a-perfect-storm-is-on-the-way>

The Mandarin (2026c, 15 July). Government’s road to surplus could run through APS ranks. <https://themandarin.com.au/316311-governments-road-to-surplus-could-run-through-aps-ranks>

When Not to Automate: A Formal Protocol for Human Preservation in AI-Optimized Organizations (2026). arXiv:2607.15944. <https://arxiv.org/abs/2607.15944>
