---
title: "The Fire Was 150 Kilometres Away and the Output Still Fell"
summary: "Australia already has a measured link between air-quality readings and lost solar generation, and now a modelled map of how far smoke travels from a fire. No published forecast puts the two together to say which half-hour the loss falls in."
themes:
  - "Emergency Management & Resilience"
image: ./117-the-fire-was-150-kilometres-away-and-the-output-still-fell.jpg
imageCredit: "Photo: Ben Shepherd, NSW Rural Fire Service, via the NSW RFS Flickr archive. Smoke over the Blue Mountains, August 2015."
queue: 117
vault: "117-the-output-still-fell.md"
release_by: 2026-12-18
---
On New Year’s Day 2020 the air quality index in Canberra passed 3,400, and rooftop solar output across the city fell by 45 per cent. No fire reached the city that day, and the sun was where it should be at the start of January. What stood between those panels and that sun was smoke, from fires burning well away from it.

That figure was published in October 2020 by the Australian Energy Council (2020), drawing on Solar Analytics readings from 35,000 sites. Sydney systems lost 15 per cent on 10 December 2019 and 27 per cent on the 21st. Across both cities the estimate for heavy smoke haze days was a drop of 15 to 45 per cent.

Six years on, a paper published in late October has modelled the same effect across the whole of south-eastern Australia. A team at the University of New South Wales used historical weather and satellite data to reconstruct solar output during the 2019-20 Black Summer and the 2009 Black Saturday fires (Poddar et al., 2026). Within about 50 kilometres of fire hotspots, Black Summer generation fell by as much as 70 per cent for several consecutive days. More than 150 kilometres out, the modelled losses still reached up to 30 per cent. Black Saturday produced about 18 per cent near hotspots and up to 10 per cent in more distant regions (UNSW Sydney, 2026).

The word doing the work in that paper’s title is “non-localised”. A solar fleet is built on the assumption that poor light is local and passing: cloud over one farm is sunshine over another, which is why geographic spread is the standard defence against solar variability. A plume still costing up to 30 per cent of output at 150 kilometres does not behave like cloud, because it dims a whole region at once and keeps dimming it for days. Spreading assets widely is no defence when the whole area sits under a single plume.

Two measured studies already sit underneath that modelling, and both produce much smaller headline numbers. In 2020 the forecasting firm Amperon worked with the Australian Energy Market Operator on twenty large-scale farms across the south-east. It used their technical specifications and electricity production data alongside counterfactual simulations, which attributed a mean decrease in generation of 4.1 per cent per plant across December 2019 and January 2020 (Amperon, n.d.). The worst single site was Mugga Lane Solar Park near Canberra at 12.0 per cent, with nearby Royalla at 8.6 per cent. Then in November 2023 came a measured study led by Ethan Ford at that same university (Ford et al., 2023). It took 30-minute energy data from 160 residential systems in New South Wales, matched against government PM2.5 monitors within five kilometres of each one. The measured shortfall across the 71 days from 6 November 2019 was 4.2 per cent of those systems’ output.

Those figures come from separate fleets and only partly overlapping periods, so their closeness proves nothing on its own. What it does show is how a fire season looks once averaged. Four per cent reads like a rounding error, yet 4.1 and 4.2 per cent are the numbers that reached the industry.

The most useful thing in that 2023 paper was not an average at all. The same paper measured a rate: PV generation falls by 13 plus or minus 2 per cent for every 100 micrograms per cubic metre of PM2.5 in the air. That rate is a transfer function between an air-quality reading and lost electricity, which is the shape a forecast needs. It has been sitting in the literature, open access, for three years.

That paper also reports when in the day those losses fall. Ford and colleagues found them spread unevenly across the day: “the strongest reductions were seen in the mornings and evenings, with the least impact around 1p.m.”. They note that a complete explanation for the pattern is not yet understood, and they drew the operational conclusion from it themselves: a fleet exposed to it may need additional energy storage (Ford et al., 2023).

Consider what that does during a smoke event. Output lost at one in the afternoon goes missing when solar is at its most abundant. Output lost at six in the evening goes missing on the ramp, when household demand climbs while the solar contribution is already falling away. Those are not equivalent losses, and smoke takes more from the second than from the first. A seasonal average of 4.1 per cent cannot see that. Neither can a worst-case figure of 70 per cent.

So the evidence base is better than the 2026 paper’s recommendations imply, and more lopsided. Australia has a measured dose-response curve in units the New South Wales air-quality network already reports hourly, and now a modelled map of how far the effect travels from a fire. What I cannot find published anywhere is the two combined: how much output, at which hour, how far from the fire front. Shukla Poddar, the 2026 paper’s corresponding author, says “we should start looking into” smoke-trajectory modelling. Bram Hoex appears on both papers, so institutional distance does not explain why the halves are still apart.

The cost of leaving it unjoined showed up fast. On 22 February 2024, three months after the Ford paper appeared, smoke rose from a fire just east of Ararat in Victoria and by mid-afternoon had reached Ballarat and Geelong, and then Melbourne. Victoria’s rooftop solar profile dipped below its mean from two o’clock. The analyst who noticed, working from AEMO’s own rooftop estimates, could conclude only that production “would have been impacted in some way” (WattClarity, 2024). A published coefficient existed by then. The public record still could not put a number on an ordinary summer fire upwind of a capital city.

Smoke’s other downstream cost does have a developed literature in this country, and it is a health one: I have written before about [smoke reaching the cardiac ward](https://russellbuzby.com/2026/08/12/smoke-reaches-the-cardiac-ward/), where the evidence moved from emergency presentations to arterial plaque because clinicians went looking for it. The energy cost has three studies behind it and no published forecast built on them.

Meanwhile the exposure keeps growing. The Clean Energy Council reports 22.0 GW of rooftop solar installed since January 2019, and more than 4.5 million homes and small businesses now have a system, with a record 1.89 GW added in the first half of 2026 (Clean Energy Council, 2026). The measurements everyone still quotes were taken at the very start of that build-out, and the 2023 coefficient rests on 160 systems totalling 312 kilowatts. That is a sound basis for a physical relationship and a thin one for a national forecast.

The practical asks here are small. The 2026 paper calls for fire information combined with wind patterns and smoke-trajectory modelling, so that an operator gets enough warning to schedule a clean or a thermal inspection. That ask needs no new agency, and the one worth adding to it is narrower still: an operator forecast reporting expected loss by half-hour rather than by season, against a coefficient that already exists.

Smoke has reduced solar generation in every Australian fire season anybody has looked at. Before this summer, the useful question is which hour of the day that loss falls in.

## References
- Amperon. (n.d.). *Attenuation of large-scale solar PV production by bushfire smoke in south-east Australia* [Case study]. https://www.amperon.co/case-studies/attenuation-of-large-scale-solar-pv-production-by-bushfire-smoke
- Australian Energy Council. (2020, October 15). *Smoke on the solar: The impact on generation*. https://www.energycouncil.com.au/analysis/smoke-on-the-solar-the-impact-on-generation/
- Clean Energy Council. (2026). *Rooftop solar and storage report, January to June 2026*. https://cleanenergycouncil.org.au/news-resources/rooftop-solar-storage-report-january-june-2026
- Ford, E., Peters, I. M., & Hoex, B. (2023). Quantifying the impact of wildfire smoke on solar photovoltaic generation in Australia. *iScience*, *27*(2), 108611. https://doi.org/10.1016/j.isci.2023.108611
- Poddar, S., Hoex, B., & Kay, M. (2026). Understanding non-localised impacts of bushfires on photovoltaic performance, reliability, and management strategies. *Solar Energy*, *320*, 115248. https://doi.org/10.1016/j.solener.2026.115248
- UNSW Sydney. (2026, October 28). *Solar farms should prepare for bushfire effects, which can reduce output by 70%*. UNSW Newsroom. https://www.unsw.edu.au/newsroom/news/2026/10/Solar-farms-prepare-bushfire-effects-reduce-output
- WattClarity. (2024, February 23). *It appears bushfire smoke was negatively impacting rooftop PV production in a material way in Victoria yesterday*. https://wattclarity.com.au/articles/2024/02/it-appears-bushfire-smoke-was-negatively-impacting-rooftop-pv-production-in-victoria-yesterday/
