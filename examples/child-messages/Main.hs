{-# LANGUAGE DeriveAnyClass #-}
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE DerivingStrategies #-}
{-# LANGUAGE OverloadedStrings #-}
module Main where

import ChildA (MsgA (..), childA)
import ChildB (MsgB (..), childB)
import GHC.Generics (Generic)
import Miso
import qualified Miso.Html as H
import Miso.JSON (FromJSON, ToJSON, encode, object, toJSON, (.=))
import Miso.String (MisoString, ms)

-- Only the parent knows the union. Generic supplies its JSON envelope.
data ParentMail = A MsgA | B MsgB
  deriving stock (Eq, Show, Generic)
  deriving anyclass (ToJSON, FromJSON)

data RootAction
  = Received ParentMail
  | Rejected MisoString
  | SendUnknown
  | SendBare
  deriving (Eq, Show)

data Model = Model
  { aCount :: Int
  , bCount :: Int
  , errorCount :: Int
  , receiptLog :: [MisoString]
  , lastError :: MisoString
  } deriving Eq

main :: IO ()
main = startApp defaultEvents app {mountPoint = Just "app"}

app :: App Model RootAction
app = (component (Model 0 0 0 [] "") updateRoot viewRoot)
  {mailbox = checkMail Received Rejected}

updateRoot :: RootAction -> Effect () () Model RootAction
updateRoot (Received (A (MsgA n))) = modify $ \m -> m
  {aCount = aCount m + 1, receiptLog = receiptLog m ++ ["A" <> ms n]}
updateRoot (Received (B (MsgB n))) = modify $ \m -> m
  {bCount = bCount m + 1, receiptLog = receiptLog m ++ ["B" <> ms n]}
updateRoot (Rejected message) = modify $ \m -> m
  {errorCount = errorCount m + 1, lastError = message}
-- Diagnostics address this component explicitly through the public mail API.
updateRoot SendUnknown = sendToSelf $ object
  ["tag" .= ("Unknown" :: MisoString), "contents" .= (7 :: Int)]
updateRoot SendBare = sendToSelf (MsgA 7)

sendToSelf :: ToJSON message => message -> Effect () () Model RootAction
sendToSelf message = do
  info <- ask
  io_ $ mail (_componentInfoId info) message

viewRoot :: Model -> View () () Model RootAction
viewRoot m = H.main_ []
  [ H.h1_ [] [text "Reusable child messages"]
  , "child-a" +> childA A
  , "child-b" +> childB B
  , H.p_ [] [text "Parent A receipts: ", H.span_ [textProp "id" "a-count"] [text (ms (aCount m))]]
  , H.p_ [] [text "Parent B receipts: ", H.span_ [textProp "id" "b-count"] [text (ms (bCount m))]]
  , H.ol_ [textProp "id" "receipt-log"] [H.li_ [] [text entry] | entry <- receiptLog m]
  , H.h2_ [] [text "Wire values"]
  , H.p_ [] [text "A envelope: ", H.code_ [textProp "id" "wire-a"] [text (encode (A (MsgA 7)))]]
  , H.p_ [] [text "B envelope: ", H.code_ [textProp "id" "wire-b"] [text (encode (B (MsgB 7)))]]
  , H.p_ [] [text "Bare MsgA: ", H.code_ [textProp "id" "bare-a"] [text (encode (MsgA 7))]]
  , H.p_ [] [text "Bare MsgB: ", H.code_ [textProp "id" "bare-b"] [text (encode (MsgB 7))]]
  , H.p_ [] [text "checkMail round trips: ", H.strong_ [textProp "id" "decode-checks"] [text decodeChecks]]
  , H.h2_ [] [text "Expected rejection checks"]
  , H.button_ [textProp "id" "send-unknown", H.onClick SendUnknown] [text "Send unknown tag"]
  , H.button_ [textProp "id" "send-bare", H.onClick SendBare] [text "Send bare MsgA"]
  , H.p_ [] [text "Rejected messages: ", H.span_ [textProp "id" "error-count"] [text (ms (errorCount m))]]
  , H.p_ [textProp "id" "last-error"] [text (lastError m)]
  ]

decodeChecks :: MisoString
decodeChecks
  | checkMail Received Rejected (toJSON (A (MsgA 7))) == Just (Received (A (MsgA 7)))
  , checkMail Received Rejected (toJSON (B (MsgB 7))) == Just (Received (B (MsgB 7))) = "PASS"
  | otherwise = "FAIL"
