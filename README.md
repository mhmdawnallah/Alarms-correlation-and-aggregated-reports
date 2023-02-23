# Alarms Correlation and Aggregated Reports
This is a proof of concept implementation of simple anomaly detectors to identify changes in monitored metrics in IHR. This often results in a lot of alarms being displayed as tables in IHR global reports. The most important events usually generate numerous alarms across multiple datasets. It's an online tool for grouping topologically or geographically related alarms that happen at the same time and providing multi-dimensional reports.


# Project Overview
This project consists of two main components:
1- A JS module to analyze and aggregate alarms
2- A VueJS component to display aggregated alarms

The JS module will be responsible for analyzing alarms and grouping them based on their topological or geographical relation and the time they occurred. The VueJS component will be responsible for displaying the aggregated alarms in a user-friendly manner.

The tool will be integrated with IHR's global report to allow users to quickly access the aggregated alarms directly from the report.

# Installation and Usage

## Prerequisites

## Installation
