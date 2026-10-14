# TESP Modeling Redesign Requirements

The existing TESP architecture is virtually non-existant, at least as a planned activity. There have been a few major studies using TESP (SGIP and DSO+T) that have utilized experience of the developers but in neither case was a comprehensive software architecture defined and implemented. In both cases, trying to get working analysis code in place was a higher priority than designing a system to do so in a considered manner. The TESP redesign being undertaken now is an attempt to fill this gap and in doing so, produce a codebase that is easier to use and extend to a particular analysis need.

This redesign is focused on the modeling of transactive systems. There are other parts of TESP that could also be redesigned to improve usability but are not within scope for this effort. Examples include APIs for data collected and post-processing and automation around installation of TESP, among others.

A primary goal of the redesign is to make modifying and extending TESP easier for it's users and developers. Given the current state of TESP, the distinction between the two can be fuzzy at times so the term "users" necessarily includes those that look at the TESP source code to figure out how they can customize it for their needs. 

The following list are the preliminary requirements for the redesign effort.

## Provide abstract classes and documentation for common modeling needs
Users that intend to tweak, modify, or extend existing code should be able to reference existing classes (and their corresponding documentation) and find their place in the class structure where their new sub-class should fit in. This should be true from both a conceptual standpoint (_e.g._ "I see how the thing I want to do is similar to these kinds of things that have been done before in TESP.") and from a code standpoint (_e.g._ "This class has a lot of the functionality I need and I just need to modify it in these few ways.").

## Software architecture that allows classes and their methods to be used more modularly during development
Classes should provide methods that are useful in doing more than just constructing the final, comprehensive transactive system model. Some of the functionality inside the class should be useful during the development of the transactive system and thus should be appropriately modularized with the class methods to allow it's flexible use.

Said differently, it needs to be possible to use the same production classes in a development or testebed environment. The sofware arctitecture needs to support a gradual development process where intermediate development and testing are not complex and provide confidence that the code that works well in one or more testbeds will function as expected in the production environment.

## Software architecture that follows the concepts in the transactive space
PNNL has been involved in the transactive energy research topic and the grid architecture research topic for a number of years and as a result, there are a number of documents that have been produced that lay a conceptual foundation for how a transactive energy system should be architected. These documents should be consulated to help guide the software architecture.

As a starting point, SEPA's TEWG produced a "TE Concept Model" document that will be informative and GWAC has produced

## Evaluate related projects for ideas, architecture models, and code
Though TESP is the longest-lived transactive-related software project, there are other related tools at PNNL that should be consulted to see how they may have addressed the transactive space. The Transactive Energy Network Template and GridAPPS-D should both be considered, to name a few. There is even a possiblity of directly using code they produced in the new TESP redesign.

Similarly, after an initial draft of the redesigned software architecture for TESP has been created, these projects should be consulted to evaluate the architecture to see what ways their work is and isn't compatible, both conceptually and in implementation.

## Visibilty into the transactive system being modeled
The software architecture should make it easy to collect the necessary data for post-processing. Furthermore, the strcuture of the data should prevent ambiguity where possible and support high levels of auditability. Since transactive mechanisms generally employ market mechanisms, being able to precisely trace the transactions that take place to support the development of business cases, cash flow statements and other similar documents provides great value to the user.

## Performance is not the highest priority, usabilty is
There's always a need for adequate performance and when you're simulation has been running for three days, having better performance seems like it should be a higher priority, the biggest challenge TESP faces now is its unapproachability, not it's performance. The software architecture needs to increase usability and as we are achieving that goal, we can start to see how much of a performance impact it has.

