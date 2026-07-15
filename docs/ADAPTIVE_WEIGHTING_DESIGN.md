# Dynamic Feedback Weighting Mechanism for E3-Hybrid Router

This document presents the mathematical formulation and design of the adaptive multi-objective weighting mechanism for the E3-Hybrid EV swarm routing algorithm.

---

## 1. Problem Formulation
In the multi-objective EV swarm routing problem, the cost of selecting an edge $e$ in the network at time step $t$ is defined as:

$$C(e, t) = w_t(t) \cdot \hat{T}(e) + w_e(t) \cdot \hat{E}(e) + w_s(t) \cdot \hat{S}(e)$$

where:
* $\hat{T}(e)$ is the normalized expected travel time on edge $e$.
* $\hat{E}(e)$ is the normalized expected energy consumption on edge $e$.
* $\hat{S}(e)$ is the normalized safety/emergency delay factor on edge $e$.
* $w_t(t), w_e(t), w_s(t)$ are the dynamic objective weights satisfying the normalization constraint:

$$\sum_{i \in \{t, e, s\}} w_i(t) = 1.0, \quad w_i(t) \ge w_i^{\text{min}}$$

In a static configuration, $w_i(t) = w_i^0$ is constant. The adaptive mechanism dynamically adjusts these weights at simulation runtime in response to the real-time physical state of the urban traffic network.

---

## 2. Feedback Variables
We define three network-level state feedback variables calculated at each simulation step:

1. **Traffic Congestion Index ($R_v$)**:
   The average ratio of vehicle speeds to their free-flow speed limits across the active fleet:
   $$R_v(t) = \frac{1}{|V_{\text{active}}|} \sum_{v \in V_{\text{active}}} \frac{v_{\text{current}}}{v_{\text{limit}}}$$
   Lower $R_v(t)$ indicates higher network-wide congestion.

2. **Energy Depletion Index ($D_e$)**:
   A function of the average State of Charge ($SoC_{\text{mean}}$) and the average charging station queue length ($Q_{\text{mean}}$):
   $$D_e(t) = \left(1.0 - \frac{1}{|V_{\text{active}}|} \sum_{v \in V_{\text{active}}} SoC_v(t)\right) + \alpha \cdot \frac{Q_{\text{mean}}(t)}{Q_{\text{capacity}}}$$
   Higher $D_e(t)$ indicates that the fleet is running out of energy and charging stations are congested.

3. **Emergency Alert Status ($I_s$)**:
   A binary indicator of whether there is an active emergency dispatch/ambulance in the network:
   $$I_s(t) = \begin{cases} 1 & \text{if active emergency vehicles } > 0 \\ 0 & \text{otherwise} \end{cases}$$

---

## 3. Weight Adaptation Law
Using the base weights $w_i^0$ (the thesis baseline weights: $w_t^0 = 0.7, w_e^0 = 0.2, w_s^0 = 0.1$), the raw adapted weights $\tilde{w}_i(t)$ are computed as:

$$\tilde{w}_t(t) = w_t^0 + \lambda_t \cdot (1.0 - R_v(t))$$
$$\tilde{w}_e(t) = w_e^0 + \lambda_e \cdot D_e(t)$$
$$\tilde{w}_s(t) = w_s^0 + \lambda_s \cdot I_s(t)$$

where $\lambda_t, \lambda_e, \lambda_s$ are the adaptation sensitivity coefficients (configured to `0.15`).

To enforce the normalization and lower bounds, the final weights are projected as:

$$\tilde{w}'_i(t) = \max\left(w_i^{\text{min}}, \tilde{w}_i(t)\right)$$

$$w_i(t) = \frac{\tilde{w}'_i(t)}{\sum_{j \in \{t, e, s\}} \tilde{w}'_j(t)}$$

We set the minimum weight bounds to prevent any single objective from being completely ignored:
* $w_t^{\text{min}} = 0.30$
* $w_e^{\text{min}} = 0.05$
* $w_s^{\text{min}} = 0.02$

---

## 4. Implementation Design in E3-Hybrid
The `RoutingContext` is extended to carry the real-time feedback state ($R_v, D_e, I_s$). When `enable_adaptive_weighting` is active, the `MultiObjectiveEdgeScorer` reads these values from the routing context at the start of each query and recalculates the weights $w_i(t)$ used by the swarm sub-engines.
