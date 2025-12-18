Hello, everyone. In this session, I will go through four main components of wcdm transformation process. Starting with Ingress. Which covers the different input types coming from various Upstream SOR systems in different forms and shapes. Second W second Ingress.

Second wcdm output, which is serialized in Json format. Here, I will break down the Json structure into different sections. And explain. In terms of different modeling dimensions of CDM.

Third, we will discuss about CDM conversion program, which transforms an event from its native Source format. To Target CDM format. By internally using a predefined transformation use engine. Built on top of mappings identified.

And finally, wcdm tooling, where I will explain all the code foundational elements required to build a wcdm toolkit. Which is then wrapped into an xdk format published into an artifactory and is being used by a client program, like explained earlier.

And would try to get into details wherever required. With that being said, let me know if there are any questions in between.

So I like to jump over the intake part with the assumption that we have access to all the required data and that in motion alert rest. And we're going to use gsfi11 message as a reference for a festival discussion.

Now, next is helium conversion program. This component acts as a bridge in between what's coming in and what's going out and the transformation business logic in between, which is being built using the mappings identified and the rules behind those. Key phases during this process could be a parser which passes the raw, even pay load into memory.
An extraction engine, which extracts all the required attributes from the payload and create an pojo instance. A validator. It on the mandatory attributes. Data and other data level checks. Transformer, which uses different celium Builders to create a CDM object based on the mapping. An output validator. And a serializer which passes the information to the downstream consumers.

Now, let's spend some time understanding the structure of serum output. At the heart of psyllium representation is workflow step. A workflow step type is a predefined schema in the CDM model. By definition, its. It represents a single state or action in the life cycle of financial trade. Which serves as a comprehensive container of that integrates different phenos modeling domains.
Meaning.
Every Json payload output. Represents a workflow step type. The seedless version of workforce step. And it can be broken down into pieces. Which? And, and each of these pieces can be mapped to either of these domains. And, as you will see. The Json output is inherently. Nested in nature.
And that is by Design. Which follows the concept of normalization through abstraction and bottom of composibility. Where the idea is to cover wide variety of asset classes through common types. And having said that, each of these? Individual pieces. Items can be further broken down. And map to either of these domains.
Now, let. Let's talk about event model.

Now, the event model captures what happened and when happened in the life cycle of a trade. A key component of event model is the business event schema. It represents the changes of state of the trade. Which basically captures the transformation of one state of trade to another. Along with any instructions.
Context and metadata needed to explain what happened and why?
An important part of business even is the primitive instruction schema, which which holds the information about product price, quantity trade identifier. Economic term, settlement terms, Etc. Which is provided to the inbuilt CDM function to calculate any aft to calculate the after State. With any prior state, if available. And that is the even model in nutsh.

Next one is product model. Which defines a financial product which is being. Traded or modified? It holds information concerning product product, taxonomy, economic terms, price quantity. Etc. Next one is process model. Now, process model manages.
Workflow progresses through various stages or approvals. Basically, it represents the functional aspect of CDM now CDM conceptually. Defines not just schema, which. Creates a certain shape of the data. But it also maintains functions. As part of the schema. Which defines how the data will be manipulated when the certain conditions are being met. As an example, when we Define the business event. Under the event model.
Created the instructions. We provided those instructions. To a inbuilt function. Which gave? El trade state. Which represented the after state of a trade that is process model. Next one is reference data model. Which? Provides who, where, when, under what condition that even Hawk got? Information about parties, accounts, Etc. There's one more called observable model, which is not written here. Which handles the market data. Rates and pricing information. Used in the trade valuations.
Ah, like, floating rate calculations, fixed rate calculation, Etc. And that's broadly. The different models for CDM and equations.
