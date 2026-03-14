"use client"

import { useEffect, useRef } from "react"
import * as d3 from "d3"

type LeadsBySourceDatum = {
  source: string
  leads: number
  color: string
}

type ProjectRevenueDatum = {
  name: string
  actual: number
  remaining: number
}

type LeadsStackedDatum = {
  date: string
  newLeads: number
  disqualified: number
}

type ProposalsDatum = {
  date: string
  proposalsSent: number
}

type RevenueDatum = {
  month: string
  revenue: number
}

type SalesPipelineDatum = {
  stage: string
  value: number
  color: string
}

export function LeadsBySourceDonutChart({
  data,
  centerLabel,
}: {
  data: LeadsBySourceDatum[]
  centerLabel: string
}) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const size = 220
    const radius = size / 2 - 8
    const innerRadius = radius * 0.6

    const total = d3.sum(data, (d) => d.leads)

    const g = svg
      .attr("viewBox", `0 0 ${size} ${size}`)
      .append("g")
      .attr("transform", `translate(${size / 2},${size / 2})`)

    const pie = d3
      .pie<LeadsBySourceDatum>()
      .value((d) => d.leads)
      .sort(null)

    const arc = d3
      .arc<d3.PieArcDatum<LeadsBySourceDatum>>()
      .innerRadius(innerRadius)
      .outerRadius(radius)

    g.selectAll(".slice")
      .data(pie(data))
      .join("path")
      .attr("class", "slice")
      .attr("d", arc)
      .attr("fill", (d) => d.data.color)
      .attr("stroke", "var(--background)")
      .attr("stroke-width", 2)

    g.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "-0.1em")
      .attr("class", "fill-foreground")
      .attr("font-size", "26px")
      .attr("font-weight", 700)
      .text(total.toLocaleString())

    g.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "1.4em")
      .attr("class", "fill-muted-foreground")
      .attr("font-size", "12px")
      .text(centerLabel)
  }, [data, centerLabel])

  return <svg ref={svgRef} className="h-48 w-full" aria-hidden />
}

export function ProjectRevenueStackedBars({
  data,
  actualColor,
  remainingColor,
}: {
  data: ProjectRevenueDatum[]
  actualColor: string
  remainingColor: string
}) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = 420
    const rowHeight = 22
    const height = data.length * (rowHeight + 8) + 16
    const margin = { top: 8, right: 12, bottom: 8, left: 12 }

    const maxValue = d3.max(data, (d) => d.actual + d.remaining) ?? 1

    const x = d3
      .scaleLinear()
      .domain([0, maxValue])
      .range([0, width - margin.left - margin.right])

    const y = d3
      .scaleBand()
      .domain(data.map((d) => d.name))
      .range([0, height - margin.top - margin.bottom])
      .padding(0.3)

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`)

    const labelColor = "var(--primary-foreground)"

    data.forEach((row) => {
      const yPos = y(row.name) ?? 0
      const barHeight = y.bandwidth()
      const actualWidth = x(row.actual)
      const remainingWidth = x(row.remaining)

      g.append("rect")
        .attr("x", 0)
        .attr("y", yPos)
        .attr("width", actualWidth)
        .attr("height", barHeight)
        .attr("rx", 6)
        .attr("fill", actualColor)

      g.append("rect")
        .attr("x", actualWidth)
        .attr("y", yPos)
        .attr("width", remainingWidth)
        .attr("height", barHeight)
        .attr("rx", 6)
        .attr("fill", remainingColor)

      g.append("text")
        .attr("x", 8)
        .attr("y", yPos + barHeight / 2)
        .attr("dominant-baseline", "middle")
        .attr("fill", labelColor)
        .attr("font-size", "10px")
        .attr("font-weight", 600)
        .text(row.name)

      g.append("text")
        .attr("x", Math.max(actualWidth - 8, 48))
        .attr("y", yPos + barHeight / 2)
        .attr("dominant-baseline", "middle")
        .attr("text-anchor", "end")
        .attr("fill", labelColor)
        .attr("font-size", "10px")
        .attr("font-weight", 600)
        .text(row.actual.toLocaleString())

      g.append("text")
        .attr("x", Math.min(actualWidth + remainingWidth - 8, width - 32))
        .attr("y", yPos + barHeight / 2)
        .attr("dominant-baseline", "middle")
        .attr("text-anchor", "end")
        .attr("fill", labelColor)
        .attr("font-size", "10px")
        .attr("font-weight", 600)
        .text(row.remaining.toLocaleString())
    })
  }, [data, actualColor, remainingColor])

  return <svg ref={svgRef} className="h-52 w-full" aria-hidden />
}

export function LeadsStackedBarChart({
  data,
  colors,
}: {
  data: LeadsStackedDatum[]
  colors: { newLeads: string; disqualified: string; background: string }
}) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = 240
    const height = 120
    const margin = { top: 10, right: 8, bottom: 16, left: 8 }

    const x = d3
      .scaleBand()
      .domain(data.map((d) => d.date))
      .range([0, width - margin.left - margin.right])
      .padding(0.3)

    const maxValue = d3.max(data, (d) => d.newLeads + d.disqualified) ?? 1

    const y = d3
      .scaleLinear()
      .domain([0, maxValue])
      .range([height - margin.top - margin.bottom, 0])

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`)

    data.forEach((row) => {
      const xPos = x(row.date) ?? 0
      const barWidth = x.bandwidth()
      const totalHeight = height - margin.top - margin.bottom

      g.append("rect")
        .attr("x", xPos)
        .attr("y", 0)
        .attr("width", barWidth)
        .attr("height", totalHeight)
        .attr("rx", 4)
        .attr("fill", colors.background)
        .attr("opacity", 0.07)

      const newLeadsHeight = totalHeight - y(row.newLeads)
      const totalStackHeight = totalHeight - y(row.newLeads + row.disqualified)
      const disqualifiedHeight = totalStackHeight - newLeadsHeight

      g.append("rect")
        .attr("x", xPos)
        .attr("y", totalHeight - newLeadsHeight)
        .attr("width", barWidth)
        .attr("height", newLeadsHeight)
        .attr("fill", colors.newLeads)

      g.append("rect")
        .attr("x", xPos)
        .attr("y", totalHeight - newLeadsHeight - disqualifiedHeight)
        .attr("width", barWidth)
        .attr("height", disqualifiedHeight)
        .attr("fill", colors.disqualified)
    })
  }, [data, colors])

  return <svg ref={svgRef} className="h-24 w-full" aria-hidden />
}

export function ProposalsAreaChart({
  data,
  color,
}: {
  data: ProposalsDatum[]
  color: string
}) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = 240
    const height = 120
    const margin = { top: 10, right: 12, bottom: 16, left: 12 }

    const x = d3
      .scalePoint()
      .domain(data.map((d) => d.date))
      .range([0, width - margin.left - margin.right])

    const maxValue = d3.max(data, (d) => d.proposalsSent) ?? 1
    const y = d3
      .scaleLinear()
      .domain([0, maxValue])
      .range([height - margin.top - margin.bottom, 0])

    const area = d3
      .area<ProposalsDatum>()
      .x((d) => x(d.date) ?? 0)
      .y0(height - margin.top - margin.bottom)
      .y1((d) => y(d.proposalsSent))
      .curve(d3.curveMonotoneX)

    const line = d3
      .line<ProposalsDatum>()
      .x((d) => x(d.date) ?? 0)
      .y((d) => y(d.proposalsSent))
      .curve(d3.curveMonotoneX)

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`)

    g.append("path")
      .datum(data)
      .attr("fill", color)
      .attr("opacity", 0.08)
      .attr("d", area)

    g.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", color)
      .attr("stroke-width", 2)
      .attr("d", line)
  }, [data, color])

  return <svg ref={svgRef} className="h-24 w-full" aria-hidden />
}

export function RevenueLineChart({
  data,
  color,
}: {
  data: RevenueDatum[]
  color: string
}) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = 320
    const height = 120
    const margin = { top: 10, right: 12, bottom: 16, left: 12 }

    const x = d3
      .scalePoint()
      .domain(data.map((d) => d.month))
      .range([0, width - margin.left - margin.right])

    const maxValue = d3.max(data, (d) => d.revenue) ?? 1
    const y = d3
      .scaleLinear()
      .domain([0, maxValue])
      .range([height - margin.top - margin.bottom, 0])

    const line = d3
      .line<RevenueDatum>()
      .x((d) => x(d.month) ?? 0)
      .y((d) => y(d.revenue))
      .curve(d3.curveMonotoneX)

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`)

    g.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", color)
      .attr("stroke-width", 2)
      .attr("d", line)

    g.selectAll("circle")
      .data(data)
      .join("circle")
      .attr("cx", (d) => x(d.month) ?? 0)
      .attr("cy", (d) => y(d.revenue))
      .attr("r", 3)
      .attr("fill", color)
  }, [data, color])

  return <svg ref={svgRef} className="h-24 w-full" aria-hidden />
}

export function SalesPipelineFunnelChart({ data }: { data: SalesPipelineDatum[] }) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = 320
    const barHeight = 26
    const gap = 10
    const height = data.length * (barHeight + gap) + 12

    const maxValue = d3.max(data, (d) => d.value) ?? 1
    const maxBarWidth = width - 40

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", "translate(0,6)")

    data.forEach((row, index) => {
      const barWidth = (row.value / maxValue) * maxBarWidth
      const xPos = (width - barWidth) / 2
      const yPos = index * (barHeight + gap)

      g.append("rect")
        .attr("x", xPos)
        .attr("y", yPos)
        .attr("width", barWidth)
        .attr("height", barHeight)
        .attr("rx", 6)
        .attr("fill", row.color)

      g.append("text")
        .attr("x", xPos + 8)
        .attr("y", yPos + barHeight / 2)
        .attr("dominant-baseline", "middle")
        .attr("font-size", "11px")
        .attr("fill", "var(--foreground)")
        .text(row.stage)

      g.append("text")
        .attr("x", xPos + barWidth - 8)
        .attr("y", yPos + barHeight / 2)
        .attr("dominant-baseline", "middle")
        .attr("text-anchor", "end")
        .attr("font-size", "11px")
        .attr("fill", "var(--foreground)")
        .text(row.value.toLocaleString())
    })
  }, [data])

  return <svg ref={svgRef} className="h-48 w-full" aria-hidden />
}
