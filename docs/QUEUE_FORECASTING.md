# Queue Forecasting & Wait Time Estimation Guide

## Mathematical Foundation: M/M/c & Erlang C
To estimate queue accumulation and customer waiting times without relying on arbitrary heuristics, Aurika applies M/M/c queueing theory where:
- **$\lambda$ (Arrival Rate)**: Expected customer arrival rate in guests per hour from the `ArrivalPredictionEngine`.
- **$\mu$ (Service Rate)**: Effective table turnover and party seating rate per active seating host / table channel.
- **$c$ (Active Servers)**: Number of active host stands or available seating channels.

### Erlang C Probability of Waiting
The probability $P_w$ that an arriving guest party must wait in the lobby queue is calculated as:
$$P_w = \frac{\frac{(c\rho)^c}{c!} \left(\frac{1}{1 - \rho}\right)}{\sum_{k=0}^{c-1} \frac{(c\rho)^k}{k!} + \frac{(c\rho)^c}{c!} \left(\frac{1}{1 - \rho}\right)}$$
where $\rho = \frac{\lambda}{c\mu}$ represents traffic intensity.

### Average & Maximum Waiting Time
The expected average wait time $W_q$ (in minutes) is defined as:
$$W_q = \left( \frac{P_w}{c\mu (1 - \rho)} \right) \times 60 + (L_q \times 1.2)$$
where $L_q$ is the forecasted queue length. The maximum waiting time is bounded at the 95th percentile ($\approx 1.85 \times W_q$).

## Overflow Probability Calculation
When projected queue length $L_q$ approaches physical lobby capacity ($C_{max} = 35$), overflow probability is derived from the upper confidence bound of the Holt-Winters forecast:
$$P(\text{Overflow}) = \max\left(0.01, \min\left(0.90, 1.0 - \frac{C_{max} - L_q}{\text{Upper Bound} - L_q}\right)\right)$$

## Bottleneck Triggers & Mitigations
- **Warning Threshold**: Average wait time $\ge 25\text{m}$ or queue length $\ge 20$ parties.
- **Critical Threshold**: Average wait time $\ge 35\text{m}$ or queue length $\ge 30$ parties.
- **Proactive Action**: When critical thresholds are forecasted within any horizon ($+5\text{m}$ to $+60\text{m}$), the system automatically elevates host seating priorities in the Decision Engine and recommends transitioning to an SMS virtual waiting list.
