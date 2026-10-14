# Agent Performance Goals

Based on a conversation with Rob Pratt about his experience helping with the agent design in DSO+T, he recommended the following as good general practices when developing a new agent and/or a new trasnactive system in which the agent can operate.

## Linear Responses to Customer-Facing Parameters

Preference expression by the customer should have a linear response in terms of loss of amenity and value (usually monetary) earned. Using the slider as an example, if the customer sets their preference to 0.5 they should be saving half as much as a customer setting their preference to 1.0 and should be feeling half the discomfort. This could be very difficult to realize but should be a goal. This is currently not the case in DSO+T.

Maybe, more generally, the customer should experience proportionality of response. They settings they get to choose from may not always be linear but should be understandable by the customer and they should know what they are getting.

## Cost-Saving Measures Should be Guaranteed to Save Money

If possible, it would be good to be able to prove that the agent, when directed to sacrifice amenity for comfort, will do so. This is likely a mathematical exercise but there may be a may to empirically test for this (or close enough).

## Demonstrate Consideration of Asset Limitations

In their asset models, agents should have attributes that allow consideration of the physical limitation of their devices to be considered. For example, an agent should attempt to change the HVAC state every thrity seconds.

## Market + Agent has Demonstrated Stability

Any particular combination of market and agent(s) should be able to demonstrate stability. If possible, a mathematical proof would be desirable but a start would be a test harness that allows us to demonstrate that, at least under common conditions, the system is stable. Maybe the test harness could include common or expected edge cases as well.
