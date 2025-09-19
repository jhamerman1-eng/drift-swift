Swift Order Subscriber
Initializing and Subscribing
The most straightforward way to connect to the websocket server and begin receiving messages is via the SwiftOrderSubscriber  which is available within the Python, Rust, and Typescript drift sdks (along with all necessary arguments and types). An example of constructing the SwiftOrderSubscriber is below:
const driftClient = new DriftClient(driftClientConfig);
const userMap = new UserMap({
		driftClient,
		connection,
		subscriptionConfig: {
			type: 'websocket',
			resubTimeoutMs: 30_000,
			commitment: 'confirmed'
		},
		skipInitialLoad: false,
		includeIdle: false,
	});

await driftClient.subscribe()
await userMap.subscribe()

const swiftOrderSubscriber = new SwiftOrderSubscriber({
				driftEnv: 'mainnet-beta',
				marketIndexes: [0, 1, 2, 3],
				/**
					In the future, this will be used for verifying $DRIFT stake as we add
					authentication for delegate signers
					For now, pass a new keypair or a keypair to an empty wallet
				*/
				keypair: new Keypair(),
				driftClient,
				userAccountGetter: userMap,
			});

Subscribing to Order Messages
To subscribe and begin using messages, call subscribe(), and provide it an onOrder() callback that will be invoked on every new order.
The onOrder callback has 2 arguments: the raw message received from the websocket server (the raw message is necessary to supply as ix data to the drift program), and the deserialized order data for inspection: SignedMsgOrderParamsMessage.
This subscription is taken care of under the hood when integrating with the JitProxyClient  (detailed in the next section). A simple callback example is provided below.

await swiftOrderSubscriber.subscribe(
		async (
			orderMessageRaw: any,
			signedMessage: | SignedMsgOrderParamsMessage
				| SignedMsgOrderParamsDelegateMessage,
			isDelegateSigner?: boolean
		) => {
			const takerAuthority = new PublicKey(orderMessageRaw['taker_authority']);
			const takerUserPubkey = isDelegateSigner
				? (signedMessage as SignedMsgOrderParamsDelegateMessage).takerPubkey
				: await getUserAccountPublicKey(
					this.driftClient.program.programId,
					takerAuthority,
					(signedMessage as SignedMsgOrderParamsMessage).subAccountId
			  );
			const orderParams = signedMessage.signedMsgOrderParams;
			console.log(
				`${takerUserPubkey.toString()} wants to ${getVariant(
					orderParams.direction
				)} ${convertToNumber(
					orderParams.baseAssetAmount,
					BASE_PRECISION
				)} units of market index ${orderParams.marketIndex}`
			);
			console.log(
				`Auction params: ${
					orderParams.auctionDuration
				} slots. Start Price: ${convertToNumber(
					orderParams.auctionStartPrice!,
					PRICE_PRECISION
				)}. End Price: ${convertToNumber(
					orderParams.auctionEndPrice!,
					PRICE_PRECISION
				)}`
			);
		}
	);

# (Recommended) Integrating with JIT

Swift is essentially an off-chain JIT extension. When takers sign a message, they include the slot when the order's auction begins. This slot is used as the auction start slot and for calculating the order's current price when the order is posted on-chain. The orders are posted either as part of a fill or when a maker trades against it.

The simplest way to abstract over the on-chain and off-chain order flows, is with the `JitProxyClient`. It uses the jit-proxy program (a wrapper program for drift) that makes it easier to market make against auction orders. To learn more about JIT or JitProxy, see the following links:

- [Drift matching engine](https://docs.drift.trade/about-v2/matching-engine)
- [JIT Maker FAQ](https://docs.drift.trade/about-v2/jit-maker-faq)
- [Jit Proxy SDK](https://github.com/drift-labs/jit-proxy/tree/master/ts/sdk)

For any additional questions on JIT, please ping the team on telegram or discord.

To integrate Swift with JIT, simply pass a `SlotSubscriber` and `SwiftOrderSubscriber` to either the `JitterSniper` or `JitterShotgun` .

One important thing to note when integrating Swift with Jitters is that orders will also come through the `AuctionSubscriber` after the order lands on-chain. For example, consider the following scenario:

1. Swift order gets sent to market maker for 100 SOL-PERP
2. Swift order arrives to your bot via `SwiftOrderSubscriber`
3. One market maker fills the size for 1 SOL-PERP and in the process posts the order on-chain
4. Order comes through the `AuctionSubscriber` with base amount filled size 1 and base amount remaining as size 99

In the above example, you can get "notified" or have callbacks executed twice for the same Swift Order — once while it's off-chain and again when it's on-chain. The drift sdk provides a method called `isSignedMsgOrder` that will detect if orders coming through the `AuctionSubscriber` were Swift orders, and you can then filter your callbacks as necessary. For convenience, the jitters accept a boolean config `auctionSubscriberIgnoresSwiftOrders` , that causes the jitters to ignore orders coming through the `AuctionSubscriber` where `isSignedMsgOrder` evaluates to true. This is set to true in the example below

```tsx
const swiftOrderSubscriber = new SwiftOrderSubscriber({
				driftEnv: 'mainnet-beta',
				marketIndexes: [0, 1, 2, 3],
				keypair: myKeypair,
				driftClient,
				userAccountGetter: userMap,
			});

const slotSubscriber = new SlotSubscriber(connection, {
	resubTimeoutMs: 30_000
});

const jitProxyClient = new JitProxyClient({
			driftClient,
			programId: new PublicKey(sdkConfig.JIT_PROXY_PROGRAM_ID!),
		});

const jitter = new JitterSniper({
		auctionSubscriber,
		driftClient,
		jitProxyClient,
		swiftOrderSubscriber,
		slotSubscriber,
		auctionSubscriberIgnoresSwiftOrders: true,
});
await jitter.subscribe();
```

The jitter will handle all the message parsing, transaction construction, and transaction sending when integrating with a JitMaker strategy. For an example of using the Jitters within a JitMaker bot, see the example open sourced bot [here](https://github.com/drift-labs/keeper-bots-v2/blob/master/src/bots/jitMaker.ts).

- [Drift matching engine](https://docs.drift.trade/about-v2/matching-engine)
- [JIT Maker FAQ](https://docs.drift.trade/about-v2/jit-maker-faq)
- [Jit Proxy SDK](https://github.com/drift-labs/jit-proxy/tree/master/ts/sdk)

For any additional questions on JIT, please ping the team on telegram or discord.

To integrate Swift with JIT, simply pass a `SlotSubscriber` and `SwiftOrderSubscriber` to either the `JitterSniper` or `JitterShotgun` .

One important thing to note when integrating Swift with Jitters is that orders will also come through the `AuctionSubscriber` after the order lands on-chain. For example, consider the following scenario:

1. Swift order gets sent to market maker for 100 SOL-PERP
2. Swift order arrives to your bot via `SwiftOrderSubscriber`
3. One market maker fills the size for 1 SOL-PERP and in the process posts the order on-chain
4. Order comes through the `AuctionSubscriber` with base amount filled size 1 and base amount remaining as size 99

In the above example, you can get "notified" or have callbacks executed twice for the same Swift Order — once while it's off-chain and again when it's on-chain. The drift sdk provides a method called `isSignedMsgOrder` that will detect if orders coming through the `AuctionSubscriber` were Swift orders, and you can then filter your callbacks as necessary. For convenience, the jitters accept a boolean config `auctionSubscriberIgnoresSwiftOrders` , that causes the jitters to ignore orders coming through the `AuctionSubscriber` where `isSignedMsgOrder` evaluates to true. This is set to true in the example below

```tsx
const swiftOrderSubscriber = new SwiftOrderSubscriber({
				driftEnv: 'mainnet-beta',
				marketIndexes: [0, 1, 2, 3],
				keypair: myKeypair,
				driftClient,
				userAccountGetter: userMap,
			});

const slotSubscriber = new SlotSubscriber(connection, {
	resubTimeoutMs: 30_000
});

const jitProxyClient = new JitProxyClient({
			driftClient,
			programId: new PublicKey(sdkConfig.JIT_PROXY_PROGRAM_ID!),
		});

const jitter = new JitterSniper({
		auctionSubscriber,
		driftClient,
		jitProxyClient,
		swiftOrderSubscriber,
		slotSubscriber,
		auctionSubscriberIgnoresSwiftOrders: true,
});
await jitter.subscribe();
```

The jitter will handle all the message parsing, transaction construction, and transaction sending when integrating with a JitMaker strategy. For an example of using the Jitters within a JitMaker bot, see the example open sourced bot [here](https://github.com/drift-labs/keeper-bots-v2/blob/master/src/bots/jitMaker.ts).
